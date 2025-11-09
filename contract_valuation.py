"""
Contract Valuation Engine
Extends the contract combinators with simple pricing capabilities
"""

from financial_contracts import *
from typing import Dict, Callable
import math


class PricingModel:
    """Simple pricing model for demonstrating contract valuation"""
    
    def __init__(self, spot_prices: Dict[str, float], 
                 risk_free_rate: float,
                 volatilities: Dict[str, float]):
        self.spot_prices = spot_prices
        self.risk_free_rate = risk_free_rate
        self.volatilities = volatilities
        self.observables: Dict[str, Callable] = {}
        
    def register_observable(self, name: str, value_func: Callable):
        """Register an observable with its valuation function"""
        self.observables[name] = value_func
        
    def black_scholes_call(self, S: float, K: float, T: float, 
                          r: float, sigma: float) -> float:
        """Black-Scholes formula for European call"""
        if T <= 0:
            return max(S - K, 0)
        
        d1 = (math.log(S/K) + (r + 0.5*sigma**2)*T) / (sigma*math.sqrt(T))
        d2 = d1 - sigma*math.sqrt(T)
        
        N = lambda x: 0.5 * (1 + math.erf(x/math.sqrt(2)))
        
        return S * N(d1) - K * math.exp(-r*T) * N(d2)
    
    def black_scholes_put(self, S: float, K: float, T: float,
                         r: float, sigma: float) -> float:
        """Black-Scholes formula for European put"""
        if T <= 0:
            return max(K - S, 0)
            
        d1 = (math.log(S/K) + (r + 0.5*sigma**2)*T) / (sigma*math.sqrt(T))
        d2 = d1 - sigma*math.sqrt(T)
        
        N = lambda x: 0.5 * (1 + math.erf(x/math.sqrt(2)))
        
        return K * math.exp(-r*T) * N(-d2) - S * N(-d1)
    
    def value_contract(self, contract: Contract) -> float:
        """Recursively value a contract based on its structure"""
        
        if isinstance(contract, Zero):
            return 0.0
            
        elif isinstance(contract, One):
            return 1.0  # One unit of currency
            
        elif isinstance(contract, Give):
            return -self.value_contract(contract.contract)
            
        elif isinstance(contract, And):
            return (self.value_contract(contract.contract1) + 
                   self.value_contract(contract.contract2))
            
        elif isinstance(contract, Scale):
            # Evaluate the observable
            obs_value = self._evaluate_observable(contract.observable)
            return obs_value * self.value_contract(contract.contract)
            
        elif isinstance(contract, Then):
            # Discount future value
            future_value = self.value_contract(contract.contract)
            T = contract.time / 365.0
            discount = math.exp(-self.risk_free_rate * T)
            return discount * future_value
            
        elif isinstance(contract, Or):
            # Take maximum of two choices (holder's option)
            return max(self.value_contract(contract.contract1),
                      self.value_contract(contract.contract2))
            
        else:
            # For complex contracts, need more sophisticated pricing
            return 0.0
    
    def _evaluate_observable(self, obs: Observable) -> float:
        """Evaluate an observable to get its current value"""
        
        # Simple parser for observable expressions
        expr = obs.name
        
        # Handle constants
        try:
            return float(expr)
        except ValueError:
            pass
        
        # Handle max expressions for options
        if expr.startswith("max(0,"):
            inner = expr[6:-1].strip()
            
            # Parse "AAPL - 100" or "100 - AAPL"
            if " - " in inner:
                parts = inner.split(" - ")
                left = parts[0].strip()
                right = parts[1].strip()
                
                try:
                    left_val = float(left)
                    right_val = self.spot_prices.get(right, 0)
                    return max(0, left_val - right_val)
                except ValueError:
                    left_val = self.spot_prices.get(left, 0)
                    right_val = float(right)
                    return max(0, left_val - right_val)
        
        # Handle direct price references
        if expr in self.spot_prices:
            return self.spot_prices[expr]
        
        # Handle custom observables
        if expr in self.observables:
            return self.observables[expr]()
        
        return 0.0


def demonstrate_valuation():
    """Show contract valuation using the pricing model"""
    
    print("=" * 80)
    print("CONTRACT VALUATION DEMONSTRATION")
    print("=" * 80)
    print()
    
    # Setup pricing model
    model = PricingModel(
        spot_prices={'AAPL': 150.0, 'GOOGL': 2800.0},
        risk_free_rate=0.05,
        volatilities={'AAPL': 0.25, 'GOOGL': 0.30}
    )
    
    print("Market Parameters:")
    print(f"  AAPL spot: ${model.spot_prices['AAPL']}")
    print(f"  Risk-free rate: {model.risk_free_rate*100}%")
    print(f"  AAPL volatility: {model.volatilities['AAPL']*100}%")
    print()
    
    # Example 1: Zero Coupon Bond
    print("1. ZERO COUPON BOND")
    print("-" * 80)
    bond = zcb(365, 1000, Currency.USD)
    value = model.value_contract(bond)
    print(f"   Contract: {bond}")
    print(f"   Value: ${value:.2f}")
    print(f"   (Theoretical: ${1000 * math.exp(-0.05):.2f})")
    print()
    
    # Example 2: In-the-money Call
    print("2. IN-THE-MONEY CALL (Strike=$100, Spot=$150)")
    print("-" * 80)
    call = european_call(100, 90, "AAPL", Currency.USD)
    value = model.value_contract(call)
    T = 90/365.0
    bs_value = model.black_scholes_call(150, 100, T, 0.05, 0.25)
    print(f"   Contract: {call}")
    print(f"   Intrinsic Value: ${max(150-100, 0):.2f}")
    print(f"   Black-Scholes Value: ${bs_value:.2f}")
    print()
    
    # Example 3: Out-of-the-money Put
    print("3. OUT-OF-THE-MONEY PUT (Strike=$100, Spot=$150)")
    print("-" * 80)
    put = european_put(100, 90, "AAPL", Currency.USD)
    value = model.value_contract(put)
    bs_value = model.black_scholes_put(150, 100, T, 0.05, 0.25)
    print(f"   Contract: {put}")
    print(f"   Intrinsic Value: ${max(100-150, 0):.2f}")
    print(f"   Black-Scholes Value: ${bs_value:.2f}")
    print()
    
    # Example 4: Straddle valuation
    print("4. STRADDLE (Call + Put)")
    print("-" * 80)
    straddle = call + put
    straddle_value = model.value_contract(straddle)
    print(f"   Contract: Combination of Call and Put")
    print(f"   Combined Value: ${straddle_value:.2f}")
    print(f"   (Sum of parts: ${bs_value + model.black_scholes_put(150, 100, T, 0.05, 0.25):.2f})")
    print()
    
    # Example 5: Bull Call Spread
    print("5. BULL CALL SPREAD (Long $100 call, Short $110 call)")
    print("-" * 80)
    long_call = european_call(100, 90, "AAPL", Currency.USD)
    short_call = Give(european_call(110, 90, "AAPL", Currency.USD))
    spread = long_call + short_call
    
    long_value = model.black_scholes_call(150, 100, T, 0.05, 0.25)
    short_value = model.black_scholes_call(150, 110, T, 0.05, 0.25)
    spread_value = long_value - short_value
    
    print(f"   Long call value: ${long_value:.2f}")
    print(f"   Short call value: -${short_value:.2f}")
    print(f"   Net spread value: ${spread_value:.2f}")
    print(f"   Max profit at expiry: ${min(150, 110) - 100:.2f}")
    print()
    
    # Example 6: Portfolio of contracts
    print("6. PORTFOLIO: Bond + Protective Put")
    print("-" * 80)
    print("   Strategy: Hold asset + Put option for downside protection")
    bond_position = Then(365, Scale(Observable("AAPL"), One(Currency.USD)))
    protective_put = european_put(140, 365, "AAPL", Currency.USD)
    portfolio = bond_position + protective_put
    
    T_long = 365/365.0
    put_value = model.black_scholes_put(150, 140, T_long, 0.05, 0.25)
    asset_value = 150 * math.exp(-0.05)
    
    print(f"   Forward on AAPL (1 year): ${asset_value:.2f}")
    print(f"   Protective put (K=140): ${put_value:.2f}")
    print(f"   Total portfolio value: ${asset_value + put_value:.2f}")
    print(f"   Floor value at expiry: $140")
    print()
    
    print("=" * 80)
    print("KEY INSIGHTS FROM VALUATION:")
    print("=" * 80)
    print("• Linearity: Value(c1 & c2) = Value(c1) + Value(c2)")
    print("• Give reverses value: Value(Give(c)) = -Value(c)")
    print("• Composition preserves additive valuation")
    print("• Complex derivatives decompose into simpler valuations")
    print("• Arbitrage-free pricing emerges from the algebra")
    print()


def demonstrate_put_call_parity():
    """Demonstrate put-call parity using contract combinators"""
    
    print("=" * 80)
    print("PUT-CALL PARITY VERIFICATION")
    print("=" * 80)
    print()
    
    model = PricingModel(
        spot_prices={'S': 100.0},
        risk_free_rate=0.05,
        volatilities={'S': 0.25}
    )
    
    K = 100
    T = 90/365.0
    S = 100
    r = 0.05
    sigma = 0.25
    
    # Calculate values
    call_value = model.black_scholes_call(S, K, T, r, sigma)
    put_value = model.black_scholes_put(S, K, T, r, sigma)
    
    # Put-Call Parity: C - P = S - K*exp(-rT)
    lhs = call_value - put_value
    rhs = S - K * math.exp(-r * T)
    
    print(f"Parameters:")
    print(f"  Spot Price: ${S}")
    print(f"  Strike: ${K}")
    print(f"  Time to maturity: {90} days")
    print(f"  Risk-free rate: {r*100}%")
    print()
    
    print(f"Option Values:")
    print(f"  Call value: ${call_value:.4f}")
    print(f"  Put value: ${put_value:.4f}")
    print()
    
    print(f"Put-Call Parity: C - P = S - K*exp(-rT)")
    print(f"  Left side (C - P): ${lhs:.4f}")
    print(f"  Right side (S - PV(K)): ${rhs:.4f}")
    print(f"  Difference: ${abs(lhs - rhs):.6f}")
    print()
    
    if abs(lhs - rhs) < 0.01:
        print("  ✓ Put-Call Parity VERIFIED!")
    else:
        print("  ✗ Parity violation detected")
    print()


if __name__ == "__main__":
    demonstrate_valuation()
    print("\n")
    demonstrate_put_call_parity()
