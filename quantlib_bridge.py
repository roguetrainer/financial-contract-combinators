"""
QuantLib Bridge for Financial Contract Combinators

This module provides an interface between the functional contract combinators
and QuantLib for professional-grade pricing and risk management (Greeks).

QuantLib provides:
- Industry-standard pricing models
- Accurate numerical methods
- Greeks (delta, gamma, vega, theta, rho)
- Term structure modeling
- Calibration capabilities
"""

import QuantLib as ql
from financial_contracts import *
from typing import Dict, Tuple, Optional
from datetime import datetime, timedelta
import numpy as np


class QuantLibPricingEngine:
    """
    Bridges contract combinators to QuantLib for pricing and Greeks calculation
    """
    
    def __init__(self, 
                 evaluation_date: datetime,
                 risk_free_curve: ql.YieldTermStructure,
                 dividend_curve: Optional[ql.YieldTermStructure] = None):
        """
        Initialize the pricing engine
        
        Args:
            evaluation_date: Valuation date
            risk_free_curve: Risk-free rate term structure
            dividend_curve: Dividend yield term structure (optional)
        """
        # Set QuantLib evaluation date
        self.evaluation_date = evaluation_date
        ql_date = ql.Date(evaluation_date.day, evaluation_date.month, evaluation_date.year)
        ql.Settings.instance().evaluationDate = ql_date
        
        # Store term structures
        self.risk_free_curve = risk_free_curve
        self.dividend_curve = dividend_curve or ql.YieldTermStructureHandle(
            ql.FlatForward(ql_date, 0.0, ql.Actual365Fixed())
        )
        
        # Market data storage
        self.spot_prices: Dict[str, float] = {}
        self.volatilities: Dict[str, float] = {}
        self.processes: Dict[str, ql.BlackScholesMertonProcess] = {}
        
    def set_market_data(self, 
                       underlying: str,
                       spot: float,
                       volatility: float):
        """Register market data for an underlying asset"""
        self.spot_prices[underlying] = spot
        self.volatilities[underlying] = volatility
        
        # Create Black-Scholes process
        spot_handle = ql.QuoteHandle(ql.SimpleQuote(spot))
        vol_handle = ql.BlackVolTermStructureHandle(
            ql.BlackConstantVol(
                ql.Settings.instance().evaluationDate,
                ql.TARGET(),
                volatility,
                ql.Actual365Fixed()
            )
        )
        
        process = ql.BlackScholesMertonProcess(
            spot_handle,
            self.dividend_curve,
            self.risk_free_curve,
            vol_handle
        )
        
        self.processes[underlying] = process
    
    def _to_ql_date(self, days_from_now: int) -> ql.Date:
        """Convert days from now to QuantLib date"""
        eval_date = ql.Settings.instance().evaluationDate
        return eval_date + ql.Period(days_from_now, ql.Days)
    
    def price_european_option(self,
                            option_type: str,
                            strike: float,
                            maturity_days: int,
                            underlying: str) -> Tuple[float, Dict[str, float]]:
        """
        Price a European option and calculate Greeks
        
        Returns:
            Tuple of (price, greeks_dict)
        """
        if underlying not in self.processes:
            raise ValueError(f"No market data for {underlying}")
        
        # Create option
        maturity = self._to_ql_date(maturity_days)
        payoff = ql.PlainVanillaPayoff(
            ql.Option.Call if option_type.lower() == "call" else ql.Option.Put,
            strike
        )
        exercise = ql.EuropeanExercise(maturity)
        option = ql.VanillaOption(payoff, exercise)
        
        # Create pricing engine
        process = self.processes[underlying]
        engine = ql.AnalyticEuropeanEngine(process)
        option.setPricingEngine(engine)
        
        # Calculate price and Greeks
        price = option.NPV()
        
        greeks = {
            'delta': option.delta(),
            'gamma': option.gamma(),
            'vega': option.vega() / 100,  # QuantLib returns vega per 1% vol change
            'theta': option.theta() / 365,  # Per day
            'rho': option.rho() / 100,  # Per 1% rate change
        }
        
        return price, greeks
    
    def price_american_option(self,
                            option_type: str,
                            strike: float,
                            maturity_days: int,
                            underlying: str,
                            steps: int = 100) -> Tuple[float, Dict[str, float]]:
        """
        Price an American option using binomial tree
        
        Returns:
            Tuple of (price, greeks_dict)
        """
        if underlying not in self.processes:
            raise ValueError(f"No market data for {underlying}")
        
        # Create option
        maturity = self._to_ql_date(maturity_days)
        payoff = ql.PlainVanillaPayoff(
            ql.Option.Call if option_type.lower() == "call" else ql.Option.Put,
            strike
        )
        exercise = ql.AmericanExercise(
            ql.Settings.instance().evaluationDate,
            maturity
        )
        option = ql.VanillaOption(payoff, exercise)
        
        # Use binomial tree for American options
        process = self.processes[underlying]
        engine = ql.BinomialVanillaEngine(process, "crr", steps)
        option.setPricingEngine(engine)
        
        # Calculate price and Greeks (binomial may not provide all Greeks)
        price = option.NPV()
        
        try:
            delta = option.delta()
        except:
            delta = 0.0
            
        try:
            gamma = option.gamma()
        except:
            gamma = 0.0
            
        try:
            vega = option.vega() / 100
        except:
            vega = 0.0
            
        try:
            theta = option.theta() / 365
        except:
            theta = 0.0
            
        try:
            rho = option.rho() / 100
        except:
            rho = 0.0
        
        greeks = {
            'delta': delta,
            'gamma': gamma,
            'vega': vega,
            'theta': theta,
            'rho': rho,
        }
        
        return price, greeks
    
    def price_barrier_option(self,
                           option_type: str,
                           barrier_type: str,
                           strike: float,
                           barrier: float,
                           maturity_days: int,
                           underlying: str) -> Tuple[float, Dict[str, float]]:
        """
        Price a barrier option
        
        barrier_type: 'DownOut', 'UpOut', 'DownIn', 'UpIn'
        """
        if underlying not in self.processes:
            raise ValueError(f"No market data for {underlying}")
        
        # Map barrier type
        barrier_type_map = {
            'DownOut': ql.Barrier.DownOut,
            'UpOut': ql.Barrier.UpOut,
            'DownIn': ql.Barrier.DownIn,
            'UpIn': ql.Barrier.UpIn,
        }
        
        maturity = self._to_ql_date(maturity_days)
        payoff = ql.PlainVanillaPayoff(
            ql.Option.Call if option_type.lower() == "call" else ql.Option.Put,
            strike
        )
        exercise = ql.EuropeanExercise(maturity)
        
        option = ql.BarrierOption(
            barrier_type_map[barrier_type],
            barrier,
            0.0,  # rebate
            payoff,
            exercise
        )
        
        # Use analytic barrier engine
        process = self.processes[underlying]
        engine = ql.AnalyticBarrierEngine(process)
        option.setPricingEngine(engine)
        
        price = option.NPV()
        
        # Try to get Greeks (may not all be available for barrier options)
        try:
            delta = option.delta()
        except:
            delta = 0.0
            
        try:
            gamma = option.gamma()
        except:
            gamma = 0.0
            
        try:
            vega = option.vega() / 100
        except:
            vega = 0.0
            
        try:
            theta = option.theta() / 365
        except:
            theta = 0.0
            
        try:
            rho = option.rho() / 100
        except:
            rho = 0.0
        
        greeks = {
            'delta': delta,
            'gamma': gamma,
            'vega': vega,
            'theta': theta,
            'rho': rho,
        }
        
        return price, greeks
    
    def price_digital_option(self,
                           option_type: str,
                           strike: float,
                           payout: float,
                           maturity_days: int,
                           underlying: str) -> Tuple[float, Dict[str, float]]:
        """Price a digital (binary) option"""
        if underlying not in self.processes:
            raise ValueError(f"No market data for {underlying}")
        
        maturity = self._to_ql_date(maturity_days)
        
        # Digital payoff
        payoff = ql.CashOrNothingPayoff(
            ql.Option.Call if option_type.lower() == "call" else ql.Option.Put,
            strike,
            payout
        )
        exercise = ql.EuropeanExercise(maturity)
        option = ql.VanillaOption(payoff, exercise)
        
        # Use analytic engine
        process = self.processes[underlying]
        engine = ql.AnalyticEuropeanEngine(process)
        option.setPricingEngine(engine)
        
        price = option.NPV()
        
        # Try to get Greeks
        try:
            delta = option.delta()
        except:
            delta = 0.0
            
        try:
            gamma = option.gamma()
        except:
            gamma = 0.0
            
        try:
            vega = option.vega() / 100
        except:
            vega = 0.0
            
        try:
            theta = option.theta() / 365
        except:
            theta = 0.0
            
        try:
            rho = option.rho() / 100
        except:
            rho = 0.0
        
        greeks = {
            'delta': delta,
            'gamma': gamma,
            'vega': vega,
            'theta': theta,
            'rho': rho,
        }
        
        return price, greeks
    
    def price_contract(self, contract: Contract, underlying_map: Dict[str, str] = None) -> Dict:
        """
        Price any contract combinator and compute Greeks
        
        This recursively walks the contract tree and prices components
        
        Args:
            contract: The contract to price
            underlying_map: Maps observable names to underlying symbols
            
        Returns:
            Dictionary with price and aggregated Greeks
        """
        underlying_map = underlying_map or {}
        
        if isinstance(contract, Zero):
            return {'price': 0.0, 'delta': 0.0, 'gamma': 0.0, 
                   'vega': 0.0, 'theta': 0.0, 'rho': 0.0}
        
        elif isinstance(contract, One):
            # One unit of currency
            return {'price': 1.0, 'delta': 0.0, 'gamma': 0.0,
                   'vega': 0.0, 'theta': 0.0, 'rho': 0.0}
        
        elif isinstance(contract, Give):
            # Reverse signs
            result = self.price_contract(contract.contract, underlying_map)
            return {k: -v for k, v in result.items()}
        
        elif isinstance(contract, And):
            # Add both contracts (linearity)
            result1 = self.price_contract(contract.contract1, underlying_map)
            result2 = self.price_contract(contract.contract2, underlying_map)
            return {k: result1[k] + result2[k] for k in result1.keys()}
        
        elif isinstance(contract, Scale):
            # Scale by constant (for now, handle only numeric observables)
            try:
                scale_factor = float(contract.observable.name)
                result = self.price_contract(contract.contract, underlying_map)
                return {k: v * scale_factor for k, v in result.items()}
            except ValueError:
                # Complex observable - would need more sophisticated handling
                return {'price': 0.0, 'delta': 0.0, 'gamma': 0.0,
                       'vega': 0.0, 'theta': 0.0, 'rho': 0.0}
        
        elif isinstance(contract, Then):
            # Discount future value
            result = self.price_contract(contract.contract, underlying_map)
            T = contract.time / 365.0
            discount = self.risk_free_curve.discount(T)
            return {k: v * discount for k, v in result.items()}
        
        elif isinstance(contract, Or):
            # Maximum of two choices (simplified - proper handling needs more context)
            result1 = self.price_contract(contract.contract1, underlying_map)
            result2 = self.price_contract(contract.contract2, underlying_map)
            # Return the more valuable option
            if result1['price'] > result2['price']:
                return result1
            else:
                return result2
        
        else:
            # Unknown contract type
            return {'price': 0.0, 'delta': 0.0, 'gamma': 0.0,
                   'vega': 0.0, 'theta': 0.0, 'rho': 0.0}


def create_flat_yield_curve(rate: float, calendar=ql.TARGET()) -> ql.YieldTermStructureHandle:
    """Create a flat yield curve"""
    today = ql.Settings.instance().evaluationDate
    curve = ql.FlatForward(today, rate, ql.Actual365Fixed())
    return ql.YieldTermStructureHandle(curve)


def demonstrate_quantlib_pricing():
    """Demonstrate QuantLib integration with contract combinators"""
    
    print("=" * 80)
    print("QUANTLIB INTEGRATION FOR PRICING & GREEKS")
    print("=" * 80)
    print()
    
    # Setup pricing engine - use today's date
    eval_date = datetime.now()
    risk_free_curve = create_flat_yield_curve(0.05)
    dividend_curve = create_flat_yield_curve(0.02)
    
    engine = QuantLibPricingEngine(eval_date, risk_free_curve, dividend_curve)
    
    # Set market data
    engine.set_market_data("AAPL", spot=150.0, volatility=0.25)
    engine.set_market_data("GOOGL", spot=2800.0, volatility=0.30)
    
    print("Market Setup:")
    print(f"  Evaluation Date: {eval_date.strftime('%Y-%m-%d')}")
    print(f"  Risk-free rate: 5.0%")
    print(f"  Dividend yield: 2.0%")
    print(f"  AAPL: Spot=$150, Vol=25%")
    print(f"  GOOGL: Spot=$2800, Vol=30%")
    print()
    
    # Example 1: European Call Option
    print("1. EUROPEAN CALL OPTION")
    print("-" * 80)
    price, greeks = engine.price_european_option("call", 150, 90, "AAPL")
    
    print(f"   Strike: $150, Maturity: 90 days, Underlying: AAPL")
    print(f"   Price: ${price:.2f}")
    print(f"   Greeks:")
    print(f"     Delta: {greeks['delta']:.4f} (sensitivity to $1 change in spot)")
    print(f"     Gamma: {greeks['gamma']:.4f} (rate of delta change)")
    print(f"     Vega:  {greeks['vega']:.4f} (sensitivity to 1% vol change)")
    print(f"     Theta: {greeks['theta']:.4f} (time decay per day)")
    print(f"     Rho:   {greeks['rho']:.4f} (sensitivity to 1% rate change)")
    print()
    
    # Example 2: European Put Option
    print("2. EUROPEAN PUT OPTION")
    print("-" * 80)
    price, greeks = engine.price_european_option("put", 150, 90, "AAPL")
    
    print(f"   Strike: $150, Maturity: 90 days, Underlying: AAPL")
    print(f"   Price: ${price:.2f}")
    print(f"   Greeks:")
    print(f"     Delta: {greeks['delta']:.4f} (negative for puts)")
    print(f"     Gamma: {greeks['gamma']:.4f}")
    print(f"     Vega:  {greeks['vega']:.4f}")
    print(f"     Theta: {greeks['theta']:.4f}")
    print(f"     Rho:   {greeks['rho']:.4f}")
    print()
    
    # Example 3: American Call Option
    print("3. AMERICAN CALL OPTION (Early Exercise Premium)")
    print("-" * 80)
    price_american, greeks_american = engine.price_american_option("call", 150, 90, "AAPL")
    price_european, _ = engine.price_european_option("call", 150, 90, "AAPL")
    
    print(f"   Strike: $150, Maturity: 90 days, Underlying: AAPL")
    print(f"   American Price: ${price_american:.2f}")
    print(f"   European Price: ${price_european:.2f}")
    print(f"   Early Exercise Premium: ${price_american - price_european:.2f}")
    print(f"   Greeks:")
    print(f"     Delta: {greeks_american['delta']:.4f}")
    print(f"     Gamma: {greeks_american['gamma']:.4f}")
    print()
    
    # Example 4: Barrier Option
    print("4. UP-AND-OUT BARRIER CALL")
    print("-" * 80)
    price_barrier, greeks_barrier = engine.price_barrier_option(
        "call", "UpOut", 150, 180, 90, "AAPL"
    )
    price_vanilla, _ = engine.price_european_option("call", 150, 90, "AAPL")
    
    print(f"   Strike: $150, Barrier: $180, Maturity: 90 days")
    print(f"   Barrier Option Price: ${price_barrier:.2f}")
    print(f"   Vanilla Option Price: ${price_vanilla:.2f}")
    print(f"   Discount from barrier: {(1 - price_barrier/price_vanilla)*100:.1f}%")
    print(f"   Greeks:")
    print(f"     Delta: {greeks_barrier['delta']:.4f}")
    print(f"     Gamma: {greeks_barrier['gamma']:.4f}")
    print()
    
    # Example 5: Digital Option
    print("5. DIGITAL CALL (Binary Option)")
    print("-" * 80)
    price_digital, greeks_digital = engine.price_digital_option(
        "call", 150, 100, 90, "AAPL"
    )
    
    print(f"   Strike: $150, Payout: $100, Maturity: 90 days")
    print(f"   Digital Option Price: ${price_digital:.2f}")
    print(f"   Greeks:")
    print(f"     Delta: {greeks_digital['delta']:.4f}")
    print(f"     Gamma: {greeks_digital['gamma']:.4f} (large near strike!)")
    print()
    
    # Example 6: Portfolio Greeks (Bull Call Spread)
    print("6. BULL CALL SPREAD - PORTFOLIO GREEKS")
    print("-" * 80)
    price_long, greeks_long = engine.price_european_option("call", 140, 90, "AAPL")
    price_short, greeks_short = engine.price_european_option("call", 160, 90, "AAPL")
    
    # Aggregate portfolio
    portfolio_price = price_long - price_short
    portfolio_greeks = {
        'delta': greeks_long['delta'] - greeks_short['delta'],
        'gamma': greeks_long['gamma'] - greeks_short['gamma'],
        'vega': greeks_long['vega'] - greeks_short['vega'],
        'theta': greeks_long['theta'] - greeks_short['theta'],
        'rho': greeks_long['rho'] - greeks_short['rho'],
    }
    
    print(f"   Long call @ $140:  ${price_long:.2f}")
    print(f"   Short call @ $160: -${price_short:.2f}")
    print(f"   Net Position:      ${portfolio_price:.2f}")
    print(f"   Portfolio Greeks:")
    print(f"     Delta: {portfolio_greeks['delta']:.4f} (directional exposure)")
    print(f"     Gamma: {portfolio_greeks['gamma']:.4f} (curvature)")
    print(f"     Vega:  {portfolio_greeks['vega']:.4f} (volatility exposure)")
    print(f"     Theta: {portfolio_greeks['theta']:.4f} (time decay)")
    print()
    
    print("=" * 80)
    print("KEY INSIGHTS:")
    print("=" * 80)
    print("• QuantLib provides production-grade pricing and Greeks")
    print("• Contract combinators provide clear structure and composition")
    print("• Greeks aggregate linearly across portfolio components")
    print("• Delta-hedging: Buy/sell underlying to neutralize delta")
    print("• Gamma risk: Exposure to large moves (convexity)")
    print("• Vega risk: Exposure to volatility changes")
    print("• Theta decay: Time works against option buyers")
    print()


def demonstrate_risk_management():
    """Show how to use Greeks for risk management"""
    
    print("=" * 80)
    print("RISK MANAGEMENT WITH GREEKS")
    print("=" * 80)
    print()
    
    # Setup - use today's date
    eval_date = datetime.now()
    risk_free_curve = create_flat_yield_curve(0.05)
    dividend_curve = create_flat_yield_curve(0.02)
    engine = QuantLibPricingEngine(eval_date, risk_free_curve, dividend_curve)
    engine.set_market_data("AAPL", spot=150.0, volatility=0.25)
    
    # Portfolio: Long 100 call options
    contracts = 100
    price, greeks = engine.price_european_option("call", 155, 90, "AAPL")
    
    print("Portfolio: 100 Long Call Options")
    print(f"  Strike: $155, Spot: $150, Maturity: 90 days")
    print(f"  Individual option price: ${price:.2f}")
    print(f"  Total portfolio value: ${price * contracts:.2f}")
    print()
    
    # Portfolio Greeks
    portfolio_delta = greeks['delta'] * contracts
    portfolio_gamma = greeks['gamma'] * contracts
    portfolio_vega = greeks['vega'] * contracts
    portfolio_theta = greeks['theta'] * contracts
    
    print("Portfolio Greeks:")
    print(f"  Delta: {portfolio_delta:.2f} shares")
    print(f"  Gamma: {portfolio_gamma:.2f}")
    print(f"  Vega:  ${portfolio_vega:.2f}")
    print(f"  Theta: ${portfolio_theta:.2f} per day")
    print()
    
    # Delta hedging
    print("DELTA HEDGING:")
    print("-" * 80)
    hedge_shares = -portfolio_delta
    print(f"  To neutralize delta, need to SHORT {abs(hedge_shares):.2f} shares")
    print(f"  This makes portfolio delta-neutral (insensitive to small moves)")
    print()
    
    # Scenario analysis
    print("SCENARIO ANALYSIS:")
    print("-" * 80)
    
    scenarios = [
        ("Stock up $5", 155.0),
        ("Stock unchanged", 150.0),
        ("Stock down $5", 145.0),
    ]
    
    for desc, new_spot in scenarios:
        # Approximate P&L using Greeks
        delta_s = new_spot - 150.0
        pnl_delta = portfolio_delta * delta_s
        pnl_gamma = 0.5 * portfolio_gamma * delta_s**2
        pnl_approx = pnl_delta + pnl_gamma
        
        print(f"  {desc} (S=${new_spot}):")
        print(f"    Delta P&L:  ${pnl_delta:+.2f}")
        print(f"    Gamma P&L:  ${pnl_gamma:+.2f}")
        print(f"    Total P&L:  ${pnl_approx:+.2f}")
    print()
    
    # Vega risk
    print("VOLATILITY RISK (VEGA):")
    print("-" * 80)
    vol_scenarios = [
        ("Vol up 5%", 0.30),
        ("Vol unchanged", 0.25),
        ("Vol down 5%", 0.20),
    ]
    
    for desc, new_vol in vol_scenarios:
        vol_change = (new_vol - 0.25) * 100  # In percentage points
        pnl_vega = portfolio_vega * vol_change
        
        print(f"  {desc} (σ={new_vol:.0%}):")
        print(f"    Vega P&L: ${pnl_vega:+.2f}")
    print()
    
    # Time decay
    print("TIME DECAY (THETA):")
    print("-" * 80)
    days_forward = [1, 7, 14, 30]
    
    for days in days_forward:
        theta_pnl = portfolio_theta * days
        print(f"  After {days} days: ${theta_pnl:+.2f}")
    print()
    
    print("=" * 80)
    print("RISK MANAGEMENT PRINCIPLES:")
    print("=" * 80)
    print("• Delta: Hedge with underlying to neutralize directional risk")
    print("• Gamma: Monitor convexity; large gamma = big delta changes")
    print("• Vega: Hedge with other options to control vol risk")
    print("• Theta: Time decay; short options gain, long options lose")
    print("• Portfolio Greeks aggregate linearly")
    print("• Greeks change over time; need continuous rehedging")
    print()


if __name__ == "__main__":
    demonstrate_quantlib_pricing()
    print("\n")
    demonstrate_risk_management()
