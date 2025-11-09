# Financial Contract Combinators - Complete Project

## 🎯 Quick Start

This project implements Simon Peyton Jones's functional approach to financial derivatives using composable contract primitives, with full QuantLib integration for professional pricing and Greeks calculation.

## 📁 Files Overview

### Core Implementation
1. **financial_contracts.py** - Primitive combinators and basic derivatives
2. **contract_valuation.py** - Simple pricing model with Black-Scholes
3. **exotic_derivatives.py** - Exotic options and structured products
4. **quantlib_bridge.py** - QuantLib integration for production pricing

### Documentation
5. **README.md** - Complete framework documentation
6. **QUANTLIB_INTEGRATION.md** - Greeks and risk management guide
7. **financial_contracts_demo.ipynb** - Interactive Jupyter notebook

## 🚀 Getting Started

### Installation

```bash
# Install required packages
pip install QuantLib-Python numpy

# Optional for notebook
pip install jupyter
```

### Basic Usage

```python
from financial_contracts import *

# Create a European call option
call = european_call(strike=100, maturity=90, underlying="AAPL", currency=Currency.USD)
print(call)
# Output: Then(90, Scale(Obs(max(0, AAPL - 100)), One(USD)))

# Build a straddle
put = european_put(strike=100, maturity=90, underlying="AAPL", currency=Currency.USD)
straddle = call + put

# Bull call spread
long_call = european_call(100, 90, "AAPL", Currency.USD)
short_call = Give(european_call(110, 90, "AAPL", Currency.USD))
bull_spread = long_call + short_call
```

### QuantLib Integration

```python
from quantlib_bridge import QuantLibPricingEngine, create_flat_yield_curve
from datetime import datetime

# Setup pricing engine
engine = QuantLibPricingEngine(
    evaluation_date=datetime.now(),
    risk_free_curve=create_flat_yield_curve(0.05),
    dividend_curve=create_flat_yield_curve(0.02)
)

# Register market data
engine.set_market_data("AAPL", spot=150.0, volatility=0.25)

# Price and get Greeks
price, greeks = engine.price_european_option("call", 150, 90, "AAPL")

print(f"Price: ${price:.2f}")
print(f"Delta: {greeks['delta']:.4f}")
print(f"Gamma: {greeks['gamma']:.4f}")
print(f"Vega:  {greeks['vega']:.4f}")
print(f"Theta: {greeks['theta']:.4f}")
```

## 🧩 The Nine Primitive Combinators

| Combinator | Purpose | Example |
|------------|---------|---------|
| `Zero` | Worthless contract | `Zero()` |
| `One(cur)` | Pay one unit | `One(Currency.USD)` |
| `Give(c)` | Reverse direction | `Give(One(USD))` |
| `And(c1,c2)` | Both contracts | `call + put` |
| `Or(c1,c2)` | Choice | `call \| put` |
| `Then(t,c)` | Delay | `Then(365, One(USD))` |
| `Scale(obs,c)` | Scale by observable | `Scale(Obs("100"), One(USD))` |
| `When(obs,c)` | Conditional | `When(Obs("AAPL>100"), c)` |
| `Truncate(t,c)` | Expiration | `Truncate(90, c)` |
| `Anytime(obs,c)` | Exercise anytime | `Anytime(Obs("profitable"), c)` |

## 📊 Example: Building a Derivative

### European Call Option

```python
def european_call(strike, maturity, underlying, currency):
    """
    Breakdown:
    1. Calculate payoff: max(0, S - K)
    2. Scale One(USD) by the payoff
    3. Delay to maturity
    """
    payoff = Observable(f"max(0, {underlying} - {strike})")
    return Then(maturity, Scale(payoff, One(currency)))
```

### Iron Condor

```python
# Four-leg strategy
short_put  = Give(european_put(95, 90, "AAPL", Currency.USD))
long_put   = european_put(90, 90, "AAPL", Currency.USD)
short_call = Give(european_call(105, 90, "AAPL", Currency.USD))
long_call  = european_call(110, 90, "AAPL", Currency.USD)

iron_condor = short_put + long_put + short_call + long_call
```

## 🎓 Key Concepts

### 1. Compositionality
Complex derivatives = composition of simple primitives

### 2. Algebraic Properties
- **Identity**: `Zero & c = c`
- **Involution**: `Give(Give(c)) = c`
- **Linearity**: `Value(c1 & c2) = Value(c1) + Value(c2)`

### 3. Put-Call Parity
Emerges naturally from the structure:
```python
call - put = forward
# Or: call + Give(put) = forward_contract
```

### 4. Greeks Linearity
```python
Greeks(c1 & c2) = Greeks(c1) + Greeks(c2)
Greeks(Give(c)) = -Greeks(c)
```

## 📈 Risk Management with Greeks

### Delta (Δ): Directional Risk
```python
portfolio_delta = 44.12 shares
hedge = -44.12 shares  # Short to neutralize
```

### Gamma (Γ): Convexity
```python
# P&L approximation
pnl = delta * Δs + 0.5 * gamma * Δs²
```

### Vega (ν): Volatility Risk
```python
# Vol increases by 5%
pnl = vega * 5
```

### Theta (Θ): Time Decay
```python
# Loss per day
daily_decay = theta
```

## 🔬 Running Examples

### Basic Demonstrations
```bash
# Contract combinators
python financial_contracts.py

# Valuation and put-call parity
python contract_valuation.py

# Exotic derivatives
python exotic_derivatives.py

# QuantLib integration and Greeks
python quantlib_bridge.py
```

### Jupyter Notebook
```bash
jupyter notebook financial_contracts_demo.ipynb
```

## 💡 Use Cases

### 1. Product Structuring
Define complex derivatives clearly and verifiably

### 2. Risk Management
Decompose portfolios into primitive exposures

### 3. Model Validation
Verify algebraic relationships (put-call parity, etc.)

### 4. Client Communication
Explain structured products transparently

### 5. Regulatory Reporting
Clear breakdown of product components

### 6. Trading Systems
Type-safe contract representation

## 🔧 Advanced Features

### Custom Derivatives
```python
def asian_call(strike, observation_dates, underlying, currency):
    """Average price option"""
    avg = Observable(f"avg({underlying} on {observation_dates})")
    payoff = Observable(f"max(0, {avg} - {strike})")
    return Then(observation_dates[-1], Scale(payoff, One(currency)))
```

### Portfolio Aggregation
```python
portfolio = (
    european_call(100, 90, "AAPL", Currency.USD) +
    european_put(95, 90, "AAPL", Currency.USD) +
    Give(european_call(105, 90, "AAPL", Currency.USD))
)

# Price entire portfolio
portfolio_value, portfolio_greeks = engine.price_contract(portfolio)
```

## 📚 References

1. **Peyton Jones, S., Eber, J-M., & Seward, J.** (2000). "Composing Contracts: An Adventure in Financial Engineering." *ICFP 2000*.

2. **QuantLib Documentation**: https://www.quantlib.org/

3. **Hull, J.C.** (2017). *Options, Futures, and Other Derivatives*. Pearson.

## 🎯 Key Insights

> **Compositionality**: Build complex from simple
> 
> **Transparency**: No black boxes
> 
> **Type Safety**: Prevent modeling errors
> 
> **Mathematical Rigor**: Algebraic properties enable reasoning
> 
> **Production Ready**: QuantLib integration for real pricing

## 🚀 Next Steps

1. **Explore the Notebook**: Start with `financial_contracts_demo.ipynb`
2. **Run Examples**: Execute each Python file to see demonstrations
3. **Read Documentation**: Check `README.md` for theory, `QUANTLIB_INTEGRATION.md` for Greeks
4. **Extend**: Add your own exotic derivatives or pricing models
5. **Integrate**: Connect to real market data feeds

## 📊 Sample Output

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

BULL CALL SPREAD - PORTFOLIO GREEKS
Long call @ $140:  $13.91
Short call @ $160: -$4.01
Net Position:      $9.90
Portfolio Greeks:
  Delta: 0.4037 (directional exposure)
  Gamma: -0.0027 (curvature)
  Vega:  -0.0381 (volatility exposure)
  Theta: 0.0017 (time decay)
```

## ✨ Benefits

### For Quants
- Clear mathematical foundation
- Algebraic reasoning about equivalences
- Type-safe construction

### For Traders
- Transparent product breakdown
- Clear risk exposures
- Portfolio aggregation

### For Risk Managers
- Component-wise risk attribution
- Greeks aggregation
- Scenario analysis

### For Developers
- Composable architecture
- Easy to test
- Maintainable codebase

## 🎉 Conclusion

This project demonstrates that **functional programming elegance** and **quantitative finance rigor** are not just compatible—they're complementary! 

The contract combinators provide clarity and structure, while QuantLib provides the computational horsepower for production pricing and risk management.

**Welcome to the intersection of theory and practice!** 🚀

---

*Built with functional programming principles and quantitative finance expertise.*
