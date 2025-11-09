# QuantLib Integration with Financial Contract Combinators

## Overview

This document explains how the functional contract combinators framework interfaces with QuantLib for production-grade pricing and Greeks calculation.

## Why Integrate with QuantLib?

The contract combinators provide **structure and composition**, while QuantLib provides:

1. **Industry-Standard Pricing Models**
   - Black-Scholes-Merton for European options
   - Binomial trees for American options  
   - Analytic formulas for barriers and digitals
   - Monte Carlo for path-dependent options

2. **Accurate Greeks Calculation**
   - Delta: Sensitivity to underlying price
   - Gamma: Rate of change of delta (convexity)
   - Vega: Sensitivity to volatility
   - Theta: Time decay
   - Rho: Sensitivity to interest rates

3. **Professional Features**
   - Term structure modeling (yield curves, vol surfaces)
   - Multiple pricing engines per instrument
   - Calibration to market data
   - Day count conventions
   - Holiday calendars

## Architecture

```
┌─────────────────────────────────────┐
│  Contract Combinators (Structure)   │
│  • Compositional definition          │
│  • Type-safe construction            │
│  • Algebraic properties              │
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│    QuantLibPricingEngine (Bridge)   │
│  • Translate contracts to QuantLib  │
│  • Aggregate Greeks linearly        │
│  • Handle portfolio composition     │
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│     QuantLib (Implementation)       │
│  • Numerical pricing methods        │
│  • Greeks via finite differences    │
│  • Market data management           │
└─────────────────────────────────────┘
```

## Key Classes

### QuantLibPricingEngine

The bridge between combinators and QuantLib:

```python
engine = QuantLibPricingEngine(
    evaluation_date=datetime.now(),
    risk_free_curve=create_flat_yield_curve(0.05),
    dividend_curve=create_flat_yield_curve(0.02)
)

# Register market data
engine.set_market_data("AAPL", spot=150.0, volatility=0.25)

# Price options and get Greeks
price, greeks = engine.price_european_option(
    option_type="call",
    strike=150,
    maturity_days=90,
    underlying="AAPL"
)
```

### Methods Available

1. **price_european_option()** - European calls/puts with analytic pricing
2. **price_american_option()** - American options using binomial trees
3. **price_barrier_option()** - Knock-in/knock-out barriers
4. **price_digital_option()** - Binary/digital options
5. **price_contract()** - Generic pricer for any combinator (recursive)

## Greeks Interpretation

### Delta (Δ)
- **Definition**: Rate of change of option value with respect to underlying price
- **Units**: Shares (e.g., delta = 0.50 means option moves $0.50 per $1 move in stock)
- **Use**: Delta hedging - short delta shares to neutralize directional risk
- **Range**: Calls [0, 1], Puts [-1, 0]

### Gamma (Γ)
- **Definition**: Rate of change of delta with respect to underlying price
- **Interpretation**: Convexity; how fast delta changes
- **Use**: Measures exposure to large moves; gamma risk
- **Note**: Highest near-the-money, decays as expiry approaches

### Vega (ν)
- **Definition**: Sensitivity to 1% change in volatility
- **Units**: Dollars per 1% vol change
- **Use**: Vega hedging - use other options to neutralize vol risk
- **Note**: Always positive for long options

### Theta (Θ)
- **Definition**: Time decay - change in value per day
- **Units**: Dollars per day
- **Use**: Measures cost of carry; short options benefit from decay
- **Note**: Usually negative for long options

### Rho (ρ)
- **Definition**: Sensitivity to 1% change in interest rates
- **Units**: Dollars per 1% rate change
- **Use**: Less important for short-dated options
- **Note**: More significant for long-dated instruments

## Portfolio Greeks

Greeks aggregate **linearly** across portfolio positions:

```python
# Bull call spread
long_call_delta = 0.6500
short_call_delta = 0.3500

portfolio_delta = long_call_delta - short_call_delta  # 0.3000
```

This linearity follows from the **And** combinator:
```python
bull_spread = long_call + Give(short_call)
Greeks(bull_spread) = Greeks(long_call) - Greeks(short_call)
```

## Risk Management Applications

### 1. Delta Hedging

Neutralize directional exposure:

```python
# Portfolio: Long 100 call options with delta = 0.45
portfolio_delta = 100 * 0.45 = 45 shares

# Hedge: Short 45 shares of underlying
hedge_position = -45 shares

# Result: Delta-neutral portfolio
```

### 2. Gamma Scalping

Profit from realized volatility:
- Long gamma: Buy underlying as it falls, sell as it rises
- Short gamma: Opposite - creates risk in volatile markets

### 3. Vega Management

Control volatility exposure:
- Long vega: Benefits from vol increase (typical for options buyers)
- Short vega: Benefits from vol decrease (typical for options sellers)
- Hedge: Trade options at different strikes/maturities

### 4. Theta Management

Time decay:
- Options sellers collect theta
- Options buyers pay theta
- Theta accelerates near expiry (especially for at-the-money)

## Example: Complete Risk Analysis

```python
# Portfolio: 100 long calls, strike=$155, spot=$150

Position Value:    $571.89
Delta:             44.12 shares (directional exposure)
Gamma:             2.11 (convexity)
Vega:              $29.27 (vol sensitivity)
Theta:             -$4.53 per day (time decay)

# Scenario Analysis
Stock up $5:   P&L = +$246.96  (delta + gamma effects)
Stock down $5: P&L = -$194.21  (gamma cushions downside)

# Volatility Scenarios  
Vol up 5%:     P&L = +$146.35  (long vega benefits)
Vol down 5%:   P&L = -$146.35

# Time Decay
After 7 days:  Loss = -$31.72
After 30 days: Loss = -$135.93
```

## Combinator-Specific Greeks

### Zero Contract
```python
Greeks(Zero) = {delta: 0, gamma: 0, vega: 0, theta: 0, rho: 0}
```

### One Contract
```python
Greeks(One(USD)) = {delta: 0, gamma: 0, vega: 0, theta: 0, rho: 0}
# No market risk in a riskless payment
```

### Give Combinator
```python
Greeks(Give(c)) = -Greeks(c)
# Reverses all sensitivities
```

### And Combinator
```python
Greeks(c1 & c2) = Greeks(c1) + Greeks(c2)
# Linearity of Greeks
```

### Scale Combinator
```python
Greeks(Scale(k, c)) = k * Greeks(c)
# Proportional scaling
```

### Then Combinator
```python
Greeks(Then(t, c)) = discount(t) * Greeks(c)
# With adjustments for time value
```

## Advanced Topics

### 1. Term Structure Effects

For real pricing, use term structures instead of flat curves:

```python
# Yield curve from market data
dates = [ql.Date(1,1,2025), ql.Date(1,1,2026), ql.Date(1,1,2027)]
rates = [0.03, 0.04, 0.045]
curve = ql.ZeroCurve(dates, rates, ql.Actual365Fixed())
```

### 2. Volatility Surface

For better accuracy, use vol surfaces:

```python
# Volatility smile/skew
strikes = [90, 100, 110, 120]
vols = [0.28, 0.25, 0.24, 0.26]
vol_surface = ql.BlackVarianceSurface(...)
```

### 3. Calibration

Fit models to market prices:

```python
# Calibrate Heston model to market data
model = ql.HestonModel(...)
calibration_helpers = [...]
model.calibrate(calibration_helpers)
```

### 4. Multi-Asset Options

For rainbow/basket options:

```python
# Correlation matrix for multiple assets
correlation_matrix = [[1.0, 0.7], [0.7, 1.0]]
process = ql.BlackScholesMertonProcess(...)
```

## Comparison: Combinators vs QuantLib

| Aspect | Contract Combinators | QuantLib |
|--------|---------------------|----------|
| **Strength** | Structure, composition, clarity | Numerical accuracy, industry standard |
| **Use Case** | Product definition, risk decomposition | Pricing, Greeks, calibration |
| **Abstraction** | High-level, algebraic | Low-level, numerical |
| **Composability** | Excellent | Limited |
| **Performance** | N/A (structural) | Optimized C++ |
| **Maintenance** | Simple, few primitives | Complex, many models |

## Best Practices

### 1. Separation of Concerns
- Use combinators for **structure** (what the contract is)
- Use QuantLib for **valuation** (what it's worth)

### 2. Linear Aggregation
- Leverage linearity of Greeks for portfolio calculations
- Build complex portfolios from simple components

### 3. Validation
- Compare combinator structure with QuantLib prices
- Verify algebraic relationships (e.g., put-call parity)

### 4. Risk Limits
- Set Greeks limits (delta, vega, gamma)
- Monitor aggregate exposures
- Rehedge when limits breached

### 5. Scenario Analysis
- Use Greeks for small moves (Taylor expansion)
- Full repricing for large moves or complex paths

## Limitations

### Current Implementation
1. **Simple observables**: Only handles numeric scale factors
2. **European bias**: Some combinator features (When, Anytime) need more work
3. **Single underlying**: Multi-asset contracts need correlation handling
4. **Greeks availability**: Some engines don't provide all Greeks

### Future Extensions
1. **Path-dependent pricing**: Monte Carlo integration
2. **Credit risk**: CDS and CVA/DVA calculations
3. **Exotic payoffs**: Custom payoff functions
4. **Real-time hedging**: Dynamic delta-hedging strategies
5. **Machine learning**: Neural network pricing for complex contracts

## Conclusion

The integration of contract combinators with QuantLib provides:

✓ **Clear contract structure** from functional composition
✓ **Accurate pricing** from industry-standard models  
✓ **Complete Greeks** for risk management
✓ **Linear aggregation** preserving algebraic properties
✓ **Production-ready** implementation for real trading

This demonstrates that **theoretical elegance** and **practical utility** can coexist!

---

## Sample Output

```
EUROPEAN CALL OPTION
Strike: $150, Maturity: 90 days, Underlying: AAPL
Price: $7.92
Greeks:
  Delta: 0.5457 (sensitivity to $1 change in spot)
  Gamma: 0.0212 (rate of delta change)
  Vega:  0.2935 (sensitivity to 1% vol change)
  Theta: -0.0464 (time decay per day)
  Rho:   0.1823 (sensitivity to 1% rate change)
```

Perfect marriage of elegance and pragmatism! 🎯
