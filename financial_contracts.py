"""
Financial Contract Combinators
Based on Simon Peyton Jones's "Composing Contracts: An Adventure in Financial Engineering"

This demonstrates how complex derivative contracts can be built from simple primitives
using functional composition.
"""

from dataclasses import dataclass
from typing import Callable, List, Tuple
from enum import Enum
from datetime import datetime, timedelta
import math


class Currency(Enum):
    USD = "USD"
    EUR = "EUR"
    GBP = "GBP"
    JPY = "JPY"


@dataclass
class Observable:
    """Represents an observable value that may vary over time"""
    name: str
    
    def __repr__(self):
        return f"Obs({self.name})"


class Contract:
    """Base class for all contracts"""
    
    def and_contract(self, other: 'Contract') -> 'Contract':
        """Combine two contracts that both execute"""
        return And(self, other)
    
    def or_contract(self, other: 'Contract') -> 'Contract':
        """Choice between two contracts"""
        return Or(self, other)
    
    def __add__(self, other):
        return self.and_contract(other)
    
    def __or__(self, other):
        return self.or_contract(other)


# ============================================================================
# PRIMITIVE CONTRACTS (The Building Blocks)
# ============================================================================

@dataclass
class Zero(Contract):
    """The worthless contract - neither party gets anything"""
    
    def __repr__(self):
        return "Zero"


@dataclass
class One(Contract):
    """Immediate payment of one unit of currency"""
    currency: Currency
    
    def __repr__(self):
        return f"One({self.currency.value})"


@dataclass
class Give(Contract):
    """Reverses the direction of a contract"""
    contract: Contract
    
    def __repr__(self):
        return f"Give({self.contract})"


@dataclass
class And(Contract):
    """Combination of two contracts, both are acquired"""
    contract1: Contract
    contract2: Contract
    
    def __repr__(self):
        return f"({self.contract1} & {self.contract2})"


@dataclass
class Or(Contract):
    """Choice between two contracts - holder chooses"""
    contract1: Contract
    contract2: Contract
    
    def __repr__(self):
        return f"({self.contract1} | {self.contract2})"


@dataclass
class Truncate(Contract):
    """Contract becomes worthless after a certain time"""
    time: int  # days from now
    contract: Contract
    
    def __repr__(self):
        return f"Truncate({self.time}, {self.contract})"


@dataclass
class Then(Contract):
    """Delays acquisition of a contract"""
    time: int  # days from now
    contract: Contract
    
    def __repr__(self):
        return f"Then({self.time}, {self.contract})"


@dataclass
class Scale(Contract):
    """Scales the value of a contract by an observable"""
    observable: Observable
    contract: Contract
    
    def __repr__(self):
        return f"Scale({self.observable}, {self.contract})"


@dataclass
class When(Contract):
    """Delays contract acquisition until an observable becomes True"""
    observable: Observable
    contract: Contract
    
    def __repr__(self):
        return f"When({self.observable}, {self.contract})"


@dataclass
class Anytime(Contract):
    """Holder may acquire contract at any time before truncation"""
    observable: Observable
    contract: Contract
    
    def __repr__(self):
        return f"Anytime({self.observable}, {self.contract})"


# ============================================================================
# DERIVED COMBINATORS (Built from primitives)
# ============================================================================

def zcb(maturity: int, notional: float, currency: Currency) -> Contract:
    """Zero Coupon Bond - receive notional at maturity"""
    return Then(maturity, Scale(Observable(str(notional)), One(currency)))


def european_call(strike: float, maturity: int, underlying: str, currency: Currency) -> Contract:
    """European call option"""
    payoff_obs = Observable(f"max(0, {underlying} - {strike})")
    return Then(maturity, Scale(payoff_obs, One(currency)))


def european_put(strike: float, maturity: int, underlying: str, currency: Currency) -> Contract:
    """European put option"""
    payoff_obs = Observable(f"max(0, {strike} - {underlying})")
    return Then(maturity, Scale(payoff_obs, One(currency)))


def american_call(strike: float, maturity: int, underlying: str, currency: Currency) -> Contract:
    """American call option - can exercise anytime before maturity"""
    payoff_obs = Observable(f"max(0, {underlying} - {strike})")
    exercise_condition = Observable(f"{underlying} > {strike}")
    return Truncate(maturity, 
                    Anytime(exercise_condition, 
                           Scale(payoff_obs, One(currency))))


def forward_contract(strike: float, maturity: int, underlying: str, currency: Currency) -> Contract:
    """Forward contract - obligation to buy at strike"""
    payoff_obs = Observable(f"{underlying} - {strike}")
    return Then(maturity, Scale(payoff_obs, One(currency)))


def swap(notional: float, fixed_rate: float, payments: List[int], currency: Currency) -> Contract:
    """Interest rate swap - fixed for floating"""
    fixed_leg = Zero()
    for payment_date in payments:
        fixed_payment = Scale(Observable(str(notional * fixed_rate)), One(currency))
        fixed_leg = fixed_leg.and_contract(Then(payment_date, fixed_payment))
    
    floating_leg = Zero()
    for payment_date in payments:
        floating_payment = Scale(Observable(f"{notional} * LIBOR"), One(currency))
        floating_leg = floating_leg.and_contract(Then(payment_date, floating_payment))
    
    return fixed_leg.and_contract(Give(floating_leg))


def barrier_option(strike: float, barrier: float, maturity: int, 
                   underlying: str, barrier_type: str, currency: Currency) -> Contract:
    """Knock-in or knock-out barrier option"""
    payoff_obs = Observable(f"max(0, {underlying} - {strike})")
    
    if barrier_type == "knock-in":
        barrier_condition = Observable(f"{underlying} > {barrier}")
        return Truncate(maturity,
                       When(barrier_condition,
                            Then(maturity, Scale(payoff_obs, One(currency)))))
    else:  # knock-out
        barrier_condition = Observable(f"{underlying} < {barrier}")
        return Truncate(maturity,
                       Truncate(maturity,
                               When(barrier_condition, 
                                   Scale(payoff_obs, One(currency)))))


# ============================================================================
# DEMONSTRATION EXAMPLES
# ============================================================================

def demonstrate_contracts():
    """Show various derivative contracts built from primitives"""
    
    print("=" * 80)
    print("FINANCIAL CONTRACT COMBINATORS")
    print("Based on Simon Peyton Jones's Functional Approach")
    print("=" * 80)
    print()
    
    # Example 1: Simple Zero Coupon Bond
    print("1. ZERO COUPON BOND (pay $1000 in 365 days)")
    print("-" * 80)
    bond = zcb(365, 1000, Currency.USD)
    print(f"   {bond}")
    print()
    
    # Example 2: European Call Option
    print("2. EUROPEAN CALL OPTION (Strike=$100, Maturity=90 days, on AAPL)")
    print("-" * 80)
    call = european_call(100, 90, "AAPL", Currency.USD)
    print(f"   {call}")
    print()
    
    # Example 3: European Put Option
    print("3. EUROPEAN PUT OPTION (Strike=$100, Maturity=90 days, on AAPL)")
    print("-" * 80)
    put = european_put(100, 90, "AAPL", Currency.USD)
    print(f"   {put}")
    print()
    
    # Example 4: Straddle (Call + Put)
    print("4. STRADDLE (Long Call + Long Put at same strike)")
    print("-" * 80)
    straddle = call + put
    print(f"   {straddle}")
    print()
    
    # Example 5: Bull Call Spread
    print("5. BULL CALL SPREAD (Long call at 100, Short call at 110)")
    print("-" * 80)
    long_call = european_call(100, 90, "AAPL", Currency.USD)
    short_call = Give(european_call(110, 90, "AAPL", Currency.USD))
    bull_spread = long_call + short_call
    print(f"   {bull_spread}")
    print()
    
    # Example 6: American Call Option
    print("6. AMERICAN CALL OPTION (Early exercise allowed)")
    print("-" * 80)
    american = american_call(100, 90, "AAPL", Currency.USD)
    print(f"   {american}")
    print()
    
    # Example 7: Forward Contract
    print("7. FORWARD CONTRACT (Obligation to buy at $100 in 180 days)")
    print("-" * 80)
    forward = forward_contract(100, 180, "AAPL", Currency.USD)
    print(f"   {forward}")
    print()
    
    # Example 8: Interest Rate Swap
    print("8. INTEREST RATE SWAP (Fixed 3% vs Floating LIBOR, quarterly payments)")
    print("-" * 80)
    payment_dates = [90, 180, 270, 360]
    irs = swap(1000000, 0.03/4, payment_dates, Currency.USD)
    print(f"   {irs}")
    print()
    
    # Example 9: Barrier Option
    print("9. KNOCK-IN BARRIER CALL (activates if price > $120)")
    print("-" * 80)
    barrier = barrier_option(100, 120, 90, "AAPL", "knock-in", Currency.USD)
    print(f"   {barrier}")
    print()
    
    # Example 10: Synthetic Forward (Call - Put)
    print("10. SYNTHETIC FORWARD (Long Call - Long Put = Forward position)")
    print("-" * 80)
    synthetic = european_call(100, 90, "AAPL", Currency.USD) + Give(european_put(100, 90, "AAPL", Currency.USD))
    print(f"    {synthetic}")
    print()
    
    print("=" * 80)
    print("KEY INSIGHTS:")
    print("=" * 80)
    print("• Complex derivatives are built from simple primitives")
    print("• Composition preserves mathematical properties")
    print("• Contracts are first-class values that can be transformed")
    print("• The algebra of contracts enables reasoning about equivalences")
    print("• No-arbitrage relationships emerge naturally from the structure")
    print()


def show_contract_algebra():
    """Demonstrate algebraic properties of contracts"""
    
    print("=" * 80)
    print("CONTRACT ALGEBRA - Mathematical Properties")
    print("=" * 80)
    print()
    
    # Zero is identity for And
    print("1. Zero is identity: Zero & c = c")
    c = One(Currency.USD)
    print(f"   {Zero()} & {c} = {Zero().and_contract(c)}")
    print()
    
    # Give is involutive: Give(Give(c)) = c
    print("2. Give is involutive: Give(Give(c)) = c")
    c = One(Currency.USD)
    print(f"   Give(Give({c})) reverses twice")
    print()
    
    # Put-Call Parity
    print("3. Put-Call Parity: Call - Put = Forward")
    print("   Long Call + Short Put = Synthetic Forward")
    strike = 100
    maturity = 90
    call = european_call(strike, maturity, "S", Currency.USD)
    put = Give(european_put(strike, maturity, "S", Currency.USD))
    synthetic_forward = call + put
    print(f"   {synthetic_forward}")
    print()
    
    # Straddle decomposition
    print("4. Straddle = Call + Put (both long)")
    call = european_call(100, 90, "S", Currency.USD)
    put = european_put(100, 90, "S", Currency.USD)
    print(f"   {call + put}")
    print()


if __name__ == "__main__":
    demonstrate_contracts()
    print("\n")
    show_contract_algebra()
