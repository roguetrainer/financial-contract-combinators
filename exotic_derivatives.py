"""
Exotic Derivatives and Structured Products
Built using contract combinators
"""

from financial_contracts import *


def asian_call(strike: float, observation_dates: List[int], 
               underlying: str, currency: Currency) -> Contract:
    """Asian (average price) call option"""
    # Average of observations
    n = len(observation_dates)
    avg_observable = Observable(f"(sum([{underlying} on dates {observation_dates}]) / {n})")
    payoff = Observable(f"max(0, avg - {strike})")
    
    return Then(observation_dates[-1], Scale(payoff, One(currency)))


def lookback_call(maturity: int, underlying: str, currency: Currency) -> Contract:
    """Lookback call - strike is minimum price over life"""
    min_observable = Observable(f"min({underlying}[0:{maturity}])")
    max_observable = Observable(f"max({underlying}[0:{maturity}])")
    payoff = Observable(f"{max_observable} - {min_observable}")
    
    return Then(maturity, Scale(payoff, One(currency)))


def rainbow_option(strike: float, maturity: int, 
                   underlyings: List[str], option_type: str,
                   currency: Currency) -> Contract:
    """Rainbow option - payoff on best/worst of multiple assets"""
    if option_type == "best-of":
        payoff = Observable(f"max(0, max([{', '.join(underlyings)}]) - {strike})")
    else:  # worst-of
        payoff = Observable(f"max(0, min([{', '.join(underlyings)}]) - {strike})")
    
    return Then(maturity, Scale(payoff, One(currency)))


def digital_call(strike: float, maturity: int, payout: float,
                underlying: str, currency: Currency) -> Contract:
    """Digital/Binary call - fixed payout if above strike"""
    indicator = Observable(f"1 if {underlying} > {strike} else 0")
    
    return Then(maturity, Scale(Observable(str(payout)), 
                               Scale(indicator, One(currency))))


def spread_option(strike: float, maturity: int,
                 underlying1: str, underlying2: str,
                 currency: Currency) -> Contract:
    """Option on the spread between two assets"""
    spread = Observable(f"{underlying1} - {underlying2}")
    payoff = Observable(f"max(0, {spread} - {strike})")
    
    return Then(maturity, Scale(payoff, One(currency)))


def cliquet_option(strikes: List[float], maturities: List[int],
                  underlying: str, currency: Currency) -> Contract:
    """Cliquet (ratchet) option - series of at-the-money options"""
    result = Zero()
    
    for i, (strike, maturity) in enumerate(zip(strikes, maturities)):
        reset_obs = Observable(f"{underlying}_reset_{i}")
        payoff = Observable(f"max(0, {underlying} - {reset_obs})")
        option = Then(maturity, Scale(payoff, One(currency)))
        result = result.and_contract(option)
    
    return result


def quanto_call(strike: float, maturity: int,
               foreign_underlying: str, fx_rate: str,
               currency: Currency) -> Contract:
    """Quanto option - foreign asset, domestic payout"""
    # Payoff in foreign terms
    foreign_payoff = Observable(f"max(0, {foreign_underlying} - {strike})")
    # Fixed exchange rate for quanto feature
    fixed_fx = Observable("FX_fixed")
    
    return Then(maturity, Scale(foreign_payoff, 
                               Scale(fixed_fx, One(currency))))


def autocallable(barrier: float, coupon: float, observation_dates: List[int],
                underlying: str, currency: Currency) -> Contract:
    """Autocallable note - early redemption if barrier hit"""
    result = Zero()
    
    for i, obs_date in enumerate(observation_dates):
        # Check if barrier hit
        barrier_hit = Observable(f"{underlying} >= {barrier}")
        # Cumulative coupon
        total_coupon = coupon * (i + 1)
        redemption = Scale(Observable(f"100 + {total_coupon}"), One(currency))
        
        # Early redemption if barrier hit
        early_call = When(barrier_hit, Then(obs_date, redemption))
        result = result.or_contract(early_call)
    
    return result


def variance_swap(strike_var: float, maturity: int,
                 underlying: str, notional: float,
                 currency: Currency) -> Contract:
    """Variance swap - exchange realized variance for strike"""
    realized_var = Observable(f"realized_variance({underlying}, {maturity})")
    payoff = Observable(f"{notional} * ({realized_var} - {strike_var})")
    
    return Then(maturity, Scale(payoff, One(currency)))


def accumulator(strike: float, knock_out: float, 
               observation_dates: List[int],
               underlying: str, shares_per_day: int,
               currency: Currency) -> Contract:
    """Accumulator - forced buying unless knocked out"""
    result = Zero()
    
    for obs_date in observation_dates:
        # Knock-out condition
        ko_condition = Observable(f"{underlying} > {knock_out}")
        
        # Daily purchase obligation
        purchase = Scale(Observable(f"{shares_per_day} * {strike}"), 
                        Give(One(currency)))
        
        # Active unless knocked out
        active = Truncate(obs_date, When(Observable(f"not {ko_condition}"),
                                        Then(obs_date, purchase)))
        result = result.and_contract(active)
    
    return result


def target_redemption_note(target: float, coupon_rate: float,
                           observation_dates: List[int],
                           underlying: str, currency: Currency) -> Contract:
    """Target Redemption Note (TARN) - terminates when target reached"""
    result = Zero()
    cumulative = 0
    
    for obs_date in observation_dates:
        # Calculate coupon based on underlying performance
        coupon_obs = Observable(f"calculate_coupon({underlying}, {coupon_rate})")
        coupon_payment = Then(obs_date, Scale(coupon_obs, One(currency)))
        
        # Check if target reached
        target_reached = Observable(f"cumulative_coupons >= {target}")
        
        # Continue paying unless target reached
        conditional_payment = When(Observable(f"not {target_reached}"),
                                  coupon_payment)
        result = result.and_contract(conditional_payment)
    
    return result


def demonstrate_exotic_derivatives():
    """Show exotic derivative structures"""
    
    print("=" * 80)
    print("EXOTIC DERIVATIVES AND STRUCTURED PRODUCTS")
    print("=" * 80)
    print()
    
    # Example 1: Asian Option
    print("1. ASIAN CALL (Average Price Option)")
    print("-" * 80)
    print("   Payoff based on average price over observation dates")
    asian = asian_call(100, [30, 60, 90], "AAPL", Currency.USD)
    print(f"   {asian}")
    print()
    
    # Example 2: Lookback Option
    print("2. LOOKBACK CALL")
    print("-" * 80)
    print("   Strike = minimum price observed, payoff = max - min")
    lookback = lookback_call(90, "AAPL", Currency.USD)
    print(f"   {lookback}")
    print()
    
    # Example 3: Rainbow Option
    print("3. RAINBOW OPTION (Best-of-3 Assets)")
    print("-" * 80)
    print("   Call on the best performer among multiple assets")
    rainbow = rainbow_option(100, 90, ["AAPL", "GOOGL", "MSFT"], 
                            "best-of", Currency.USD)
    print(f"   {rainbow}")
    print()
    
    # Example 4: Digital Option
    print("4. DIGITAL/BINARY CALL")
    print("-" * 80)
    print("   Fixed $100 payout if spot > strike, else nothing")
    digital = digital_call(100, 90, 100, "AAPL", Currency.USD)
    print(f"   {digital}")
    print()
    
    # Example 5: Spread Option
    print("5. SPREAD OPTION")
    print("-" * 80)
    print("   Option on the spread between two assets")
    spread = spread_option(0, 90, "AAPL", "MSFT", Currency.USD)
    print(f"   {spread}")
    print()
    
    # Example 6: Cliquet Option
    print("6. CLIQUET (RATCHET) OPTION")
    print("-" * 80)
    print("   Series of options with strikes reset at each period")
    cliquet = cliquet_option([100, 105, 110], [30, 60, 90], 
                            "AAPL", Currency.USD)
    print(f"   {cliquet}")
    print()
    
    # Example 7: Quanto Option
    print("7. QUANTO CALL")
    print("-" * 80)
    print("   Foreign asset, domestic currency payout at fixed FX rate")
    quanto = quanto_call(100, 90, "NIKKEI", "USDJPY", Currency.USD)
    print(f"   {quanto}")
    print()
    
    # Example 8: Autocallable
    print("8. AUTOCALLABLE NOTE")
    print("-" * 80)
    print("   Early redemption if barrier hit, with accumulated coupons")
    autocall = autocallable(110, 5.0, [30, 60, 90], "AAPL", Currency.USD)
    print(f"   Structure with quarterly observations")
    print()
    
    # Example 9: Variance Swap
    print("9. VARIANCE SWAP")
    print("-" * 80)
    print("   Exchange realized variance for strike variance")
    var_swap = variance_swap(0.04, 365, "AAPL", 1000000, Currency.USD)
    print(f"   {var_swap}")
    print()
    
    # Example 10: Accumulator
    print("10. ACCUMULATOR")
    print("-" * 80)
    print("    Forced daily buying unless knock-out triggered")
    dates = list(range(1, 91))
    accum = accumulator(100, 120, dates, "AAPL", 100, Currency.USD)
    print(f"    Daily obligation to buy 100 shares at $100")
    print(f"    Knocked out if price exceeds $120")
    print()
    
    print("=" * 80)
    print("STRUCTURED PRODUCTS INSIGHTS:")
    print("=" * 80)
    print("• Path-dependent payoffs combine When, Then, and Scale")
    print("• Multi-asset products use complex Observable expressions")
    print("• Early termination uses Truncate and When combinators")
    print("• Even exotic structures decompose into primitive contracts")
    print("• The algebra remains consistent regardless of complexity")
    print()


def demonstrate_structured_products():
    """Show structured product examples"""
    
    print("=" * 80)
    print("RETAIL STRUCTURED PRODUCTS")
    print("=" * 80)
    print()
    
    # Example 1: Principal Protected Note
    print("1. PRINCIPAL PROTECTED NOTE (100% protected, 80% equity upside)")
    print("-" * 80)
    print("   Zero coupon bond + Call option")
    
    bond = zcb(365, 100, Currency.USD)
    call = european_call(100, 365, "SPX", Currency.USD)
    scaled_call = Scale(Observable("0.8"), call)
    ppn = bond + scaled_call
    
    print(f"   Structure: 100% principal + 80% of upside")
    print(f"   Worst case: Return of principal")
    print(f"   Best case: Principal + 80% of index gains")
    print()
    
    # Example 2: Reverse Convertible
    print("2. REVERSE CONVERTIBLE (High coupon, downside risk)")
    print("-" * 80)
    print("   Bond + Short put on equity")
    
    coupon_dates = [90, 180, 270, 365]
    coupons = Zero()
    for date in coupon_dates:
        coupon = Then(date, Scale(Observable("2.5"), One(Currency.USD)))
        coupons = coupons + coupon
    
    principal = Then(365, Scale(Observable("100"), One(Currency.USD)))
    short_put = Give(european_put(80, 365, "AAPL", Currency.USD))
    
    reverse_conv = coupons + principal + short_put
    
    print(f"   10% annual coupon (2.5% quarterly)")
    print(f"   Risk: If AAPL < $80, receive shares instead of principal")
    print()
    
    # Example 3: Range Accrual
    print("3. RANGE ACCRUAL NOTE")
    print("-" * 80)
    print("   Coupon accrues only when underlying stays in range")
    
    obs_dates = list(range(1, 366))
    range_condition = Observable("50 < AAPL < 150")
    
    print(f"   Daily accrual of 0.03% if $50 < AAPL < $150")
    print(f"   Maximum coupon: 10.95% if always in range")
    print()
    
    # Example 4: Dual Currency Deposit
    print("4. DUAL CURRENCY DEPOSIT")
    print("-" * 80)
    print("   Higher interest, but may redeem in different currency")
    
    usd_redemption = Then(90, Scale(Observable("100000"), One(Currency.USD)))
    eur_redemption = Then(90, Scale(Observable("90000"), One(Currency.EUR)))
    
    fx_condition = Observable("EURUSD < 1.10")
    dual_currency = When(fx_condition, usd_redemption).or_contract(
                   When(Observable("not (EURUSD < 1.10)"), eur_redemption))
    
    print(f"   Deposit $100,000 at enhanced rate")
    print(f"   If EUR/USD < 1.10 at maturity: redeem in USD")
    print(f"   If EUR/USD >= 1.10: redeem €90,000 (potential loss)")
    print()
    
    print("=" * 80)
    print("STRUCTURED PRODUCT PATTERNS:")
    print("=" * 80)
    print("• Principal protection = ZCB + options")
    print("• Enhanced yield = selling optionality (short options)")
    print("• Path dependency = series of When/Then conditions")
    print("• Multi-asset = Or combinator for worst-of structures")
    print("• All products decompose into transparent primitives")
    print()


def demonstrate_real_world_strategies():
    """Show real-world trading strategies"""
    
    print("=" * 80)
    print("REAL-WORLD TRADING STRATEGIES")
    print("=" * 80)
    print()
    
    # Collar
    print("1. COLLAR (Protective Put + Covered Call)")
    print("-" * 80)
    stock = Then(0, Scale(Observable("AAPL"), One(Currency.USD)))
    protective_put = european_put(90, 365, "AAPL", Currency.USD)
    covered_call = Give(european_call(110, 365, "AAPL", Currency.USD))
    collar = stock + protective_put + covered_call
    
    print(f"   Long stock + Long put ($90) + Short call ($110)")
    print(f"   Limits both gains and losses")
    print(f"   Often zero-cost if premium offsets")
    print()
    
    # Iron Condor
    print("2. IRON CONDOR")
    print("-" * 80)
    short_put = Give(european_put(95, 90, "AAPL", Currency.USD))
    long_put = european_put(90, 90, "AAPL", Currency.USD)
    short_call = Give(european_call(105, 90, "AAPL", Currency.USD))
    long_call = european_call(110, 90, "AAPL", Currency.USD)
    
    iron_condor = short_put + long_put + short_call + long_call
    
    print(f"   Profit if underlying stays between $95-$105")
    print(f"   Maximum profit: net premium received")
    print(f"   Risk: Outside the wings ($90-$110)")
    print()
    
    # Calendar Spread
    print("3. CALENDAR SPREAD (Time Spread)")
    print("-" * 80)
    near_call = Give(european_call(100, 30, "AAPL", Currency.USD))
    far_call = european_call(100, 90, "AAPL", Currency.USD)
    calendar = near_call + far_call
    
    print(f"   Short near-term call, Long far-term call (same strike)")
    print(f"   Profits from time decay differential")
    print(f"   Vega positive (benefits from vol increase)")
    print()
    
    # Butterfly
    print("4. BUTTERFLY SPREAD")
    print("-" * 80)
    lower_call = european_call(95, 90, "AAPL", Currency.USD)
    middle_calls = Give(Scale(Observable("2"), 
                             european_call(100, 90, "AAPL", Currency.USD)))
    upper_call = european_call(105, 90, "AAPL", Currency.USD)
    
    butterfly = lower_call + middle_calls + upper_call
    
    print(f"   Long 1x $95 call, Short 2x $100 calls, Long 1x $105 call")
    print(f"   Maximum profit if underlying = $100 at expiration")
    print(f"   Limited risk, limited reward")
    print()
    
    print("=" * 80)
    print("STRATEGY INSIGHTS:")
    print("=" * 80)
    print("• Complex strategies = combinations of simple options")
    print("• Risk/reward profiles emerge from primitive composition")
    print("• Greeks (delta, gamma, vega, theta) aggregate linearly")
    print("• Portfolio risk managed through contract algebra")
    print("• Transparency: each component is explicit and priced")
    print()


if __name__ == "__main__":
    demonstrate_exotic_derivatives()
    print("\n")
    demonstrate_structured_products()
    print("\n")
    demonstrate_real_world_strategies()
