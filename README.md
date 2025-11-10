# Financial Contract Combinators

A Python implementation of Simon Peyton Jones's functional approach to modeling financial derivatives, based on his seminal paper **"Composing Contracts: An Adventure in Financial Engineering"** (2000).

![FCC](./compositional-contracts.png)

## Overview

This implementation demonstrates how complex financial derivatives can be elegantly constructed from simple, composable primitives using functional programming principles. The key insight is that financial contracts form an algebra where complex instruments are built through composition of simpler building blocks.

## Core Philosophy

**"The whole is the sum of its parts"** - Financial derivatives, no matter how complex, can be decomposed into fundamental operations:
- **Payment** (One)
- **Combination** (And)
- **Choice** (Or)
- **Delay** (Then)
- **Scaling** (Scale)
- **Reversal** (Give)

## Project Structure

```
.
├── financial_contracts.py      # Core primitives and basic derivatives
├── contract_valuation.py       # Pricing models and valuation
├── exotic_derivatives.py       # Exotic options and structured products
└── README.md                   # This file
```

## Primitive Contracts

### Zero
The worthless contract - neither party receives anything.

```python
Zero()
```

### One(currency)
Immediate payment of one unit of currency.

```python
One(Currency.USD)
```

### Give(contract)
Reverses the direction of a contract (transforms rights to obligations).

```python
Give(One(Currency.USD))  # Obligation to pay $1
```

### And(contract1, contract2)
Combination of two contracts - both are acquired.

```python
call + put  # Straddle
```

### Or(contract1, contract2)
Choice between two contracts - holder chooses which to execute.

```python
call | put  # Chooser option
```

### Then(time, contract)
Delays the acquisition of a contract.

```python
Then(365, One(Currency.USD))  # $1 in one year
```

### Scale(observable, contract)
Scales the value of a contract by an observable quantity.

```python
Scale(Observable("AAPL"), One(Currency.USD))  # Worth AAPL shares
```

### When(observable, contract)
Acquires contract when an observable condition becomes true.

```python
When(Observable("AAPL > 100"), contract)  # Exercise when condition met
```

### Truncate(time, contract)
Contract becomes worthless after a certain time.

```python
Truncate(90, contract)  # Expires in 90 days
```

### Anytime(observable, contract)
Holder may acquire contract anytime the observable condition holds.

```python
Anytime(Observable("AAPL > strike"), payoff)  # American option
```

## Examples

### 1. Zero Coupon Bond

```python
def zcb(maturity: int, notional: float, currency: Currency) -> Contract:
    return Then(maturity, Scale(Observable(str(notional)), One(currency)))

bond = zcb(365, 1000, Currency.USD)
# Result: Then(365, Scale(Obs(1000), One(USD)))
```

### 2. European Call Option

```python
def european_call(strike: float, maturity: int, underlying: str, 
                 currency: Currency) -> Contract:
    payoff_obs = Observable(f"max(0, {underlying} - {strike})")
    return Then(maturity, Scale(payoff_obs, One(currency)))

call = european_call(100, 90, "AAPL", Currency.USD)
```

### 3. Straddle (Call + Put)

```python
call = european_call(100, 90, "AAPL", Currency.USD)
put = european_put(100, 90, "AAPL", Currency.USD)
straddle = call + put
```

### 4. Bull Call Spread

```python
long_call = european_call(100, 90, "AAPL", Currency.USD)
short_call = Give(european_call(110, 90, "AAPL", Currency.USD))
bull_spread = long_call + short_call
```

### 5. American Call Option

```python
def american_call(strike: float, maturity: int, underlying: str,
                 currency: Currency) -> Contract:
    payoff_obs = Observable(f"max(0, {underlying} - {strike})")
    exercise_condition = Observable(f"{underlying} > {strike}")
    return Truncate(maturity, 
                   Anytime(exercise_condition, 
                          Scale(payoff_obs, One(currency))))
```

## Algebraic Properties

The contract combinators satisfy important algebraic laws:

### Identity
```
Zero & c = c
```

### Commutativity
```
c1 & c2 = c2 & c1
```

### Involution
```
Give(Give(c)) = c
```

### Put-Call Parity
```
Call - Put = Forward
```
This relationship emerges naturally from the combinator structure:
```python
call + Give(put) = forward_contract
```

## Valuation

The library includes a simple pricing model that demonstrates how valuations compose:

```python
model = PricingModel(
    spot_prices={'AAPL': 150.0},
    risk_free_rate=0.05,
    volatilities={'AAPL': 0.25}
)

value = model.value_contract(contract)
```

Key properties:
- **Linearity**: `Value(c1 & c2) = Value(c1) + Value(c2)`
- **Reversal**: `Value(Give(c)) = -Value(c)`
- **Discounting**: `Value(Then(t, c)) = exp(-r*t) * Value(c)`

## Exotic Derivatives

The framework naturally extends to exotic derivatives:

### Asian Options
Average price options with multiple observation dates.

### Lookback Options
Strike determined by historical min/max prices.

### Rainbow Options
Multi-asset options (best-of, worst-of).

### Digital Options
Binary payoffs based on conditions.

### Barrier Options
Knock-in/knock-out based on barriers.

### Variance Swaps
Exchange realized variance for strike variance.

## Structured Products

Complex retail products built from primitives:

### Principal Protected Notes
```python
ppn = zcb(365, 100, Currency.USD) + 
      Scale(Observable("0.8"), 
            european_call(100, 365, "SPX", Currency.USD))
```

### Reverse Convertibles
High coupon notes with short put exposure.

### Autocallables
Early redemption notes with barrier conditions.

### Range Accruals
Coupons that accrue when underlying stays in range.

## Mathematical Foundations

### Contract Algebra
Contracts form a **commutative semiring** with:
- Addition: `And` combinator
- Multiplication: Sequential composition
- Zero element: `Zero` contract
- Unit element: `One` contract

### No-Arbitrage Conditions
Arbitrage relationships emerge naturally:
- Put-call parity
- Forward pricing
- Covered interest parity

### Pricing Functionals
Valuation is a **linear functional** preserving:
- Additivity: `V(c1 + c2) = V(c1) + V(c2)`
- Homogeneity: `V(k * c) = k * V(c)`
- Time value: `V(Then(t, c)) = exp(-r*t) * V(c)`

## Advantages of This Approach

### 1. Compositionality
Complex derivatives are transparent combinations of simpler parts.

### 2. Type Safety
Contract structure prevents many modeling errors.

### 3. Mathematical Rigor
Algebraic properties enable reasoning about equivalences.

### 4. Reusability
Building blocks are reused across many products.

### 5. Transparency
No "black box" - every component is explicit.

### 6. Testing
Individual primitives can be tested in isolation.

## Real-World Applications

This approach is used in:
- **Trading systems**: For product definition and pricing
- **Risk management**: Decomposing portfolio exposures
- **Regulatory reporting**: Transparent product breakdown
- **Client communication**: Explaining structured products
- **Model validation**: Checking pricing consistency

## Extensions

The framework can be extended with:

1. **Credit risk**: Add default observables and recovery contracts
2. **Collateralization**: Model CSA and margin agreements
3. **Multi-currency**: Cross-currency basis and quanto features
4. **Early exercise**: American and Bermudan features
5. **Path dependency**: Complex exotic payoffs
6. **Market conventions**: Day count, holiday calendars

## Running the Examples

```bash
# Basic contracts and primitives
python financial_contracts.py

# Contract valuation
python contract_valuation.py

# Exotic derivatives
python exotic_derivatives.py
```

## References

1. **Peyton Jones, S., Eber, J-M., & Seward, J.** (2000). "Composing Contracts: An Adventure in Financial Engineering." *ICFP 2000*.

2. **Botta, N., Jansson, P., & Ionescu, C.** (2017). "The Impact of the Lambda Calculus in Logic and Computer Science." *Bulletin of Symbolic Logic*.

3. **Eber, J-M.** (1999). "Compositional Specification of Financial Contracts." *PhD Thesis, École Polytechnique*.

## See also:
* https://www.lexifi.com/
* https://www.lexifi.com/technology/algebra/
* https://fssnip.net/9z/title/DSL-for-financial-contracts
* https://thehedgefundjournal.com/fincad-multi-asset-derivatives-analytics/ ("_It can snap together financial contracts like Lego building blocks. Single cash-flows or legs of cash-flows can be combined to represent almost any financial product._")

## Key Insights

> "The great power of functional programming is that it allows us to build complex systems from simple, well-understood components through composition." - Simon Peyton Jones

This implementation demonstrates:
- **Modularity**: Each contract is independently understandable
- **Correctness**: Type system prevents many errors
- **Transparency**: No hidden assumptions or magic
- **Elegance**: Complex ideas expressed simply
- **Practicality**: Real derivatives built from theory

## Conclusion

The functional approach to financial contracts provides a principled foundation for derivative modeling. By treating contracts as first-class composable values, we gain:

- Mathematical rigor without sacrificing expressiveness
- Type safety without sacrificing flexibility  
- Abstraction without sacrificing performance
- Simplicity without sacrificing power

This is the power of functional programming applied to finance.
