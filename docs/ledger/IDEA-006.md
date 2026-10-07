# IDEA-006 — Risk-constrained Kelly (RCK) sizing for the C1 book

- Date / author: 2026-10-06 / SYZ (paper suggested by a friend; assessed and drafted with Claude)
- Status: open — **⚠ RECOMMENDED — NOT DECIDED**
- What: use the risk-constrained Kelly framework (Busseti, Ryu & Boyd 2016, "Risk-Constrained Kelly Gambling", https://web.stanford.edu/~boyd/papers/pdf/kelly.pdf; L-37) to set the C1 book's gross exposure and weights: maximise expected log wealth subject to a drawdown-probability constraint, instead of choosing exposure by judgement (IDEA-004 §3) or by the ad hoc 1% / 2σ₅ rule (I-61, G-29).
- Why it might help: drawdown is now part of the organisers' assessment (F-115), not only the tie-break (F-45). RCK makes the growth-versus-drawdown trade-off explicit, with a few pre-registered inputs (α, β, the return prior) that are easy to log and audit. Its constraints match ours (long-only, cash allowed, linear caps). In the paper's examples RCK beats fractional Kelly at equal drawdown risk.
- Cost / risk: about 1 day to build on the vendor data once D-09 is settled. Main risks: the expected-return input (P-07's objection to Kelly sizing still applies), the iid assumption, and an infinite-horizon guarantee that does not match a 10-session run.
- Links: P-07, G-21, G-22, G-29, I-61, I-62, I-66, F-45, F-115, Q-39, L-35, L-36, L-37, IDEA-004, IDEA-005, GAP-53, GAP-54

## 1. What the paper says
- Kelly problem: maximise E log(rᵀb) subject to 1ᵀb = 1, b ≥ 0 (b includes cash). The paper adds the drawdown requirement Prob(W_min < α) < β and replaces it with a convex sufficient condition: with λ = log β / log α, **E (rᵀb)^(−λ) ≤ 1 ⟹ Prob(W_min < α) < β**. This is the RCK problem, solvable with CVXPY for finite outcomes (or scenario samples) and by a primal-dual stochastic gradient method in general. A quadratic approximation reduces to a Markowitz portfolio.
- Examples (n = 20 assets): Kelly reaches growth 0.062 with drawdown risk 39.7%; RCK (λ = 5.5) reaches growth 0.047 at 9.9% risk; fractional Kelly at the same 10% risk reaches ≈ 0.035. The realised risk is about 30% below the bound.
- Assumptions: iid returns, a known distribution (or a large sample), cash available, and W_min taken over an **infinite** horizon.

## 2. Does it help us?
- **Yes, for sizing; no, for edge.** It is a principled answer to "how much should C1 hold?" and fits our constraints exactly. It does not create a return source: with a zero expected-return prior the optimum is all cash, so a positive exposure always rests on a pre-registered belief in a positive equity premium. Organiser preference for trading (F-115) is a separate reason to be invested.
- **The infinite-horizon bound is the wrong horizon for a 10-session run.** For a low-drift asset, eventually breaching any floor is likely, so the bound forces very small positions. The illustration below (§3) gives 4% gross at a 6%/yr premium for α = 0.92, β = 0.10, while the probability of the same 8% drawdown *within 10 sessions* at 40% gross is ≈ 0.2%.
- **So adapt it:** keep the paper's objective and its use of a drawdown-probability constraint, but evaluate the constraint over the run horizon by simulation, and keep the RCK bound only as a conservative cross-check.

## 3. Illustration (synthetic assumptions, not market data)
Four US names with assumed daily vols 1.8/2.0/3.0/3.8%, betas 1.0/1.05/1.5/1.8, pairwise correlation 0.55, Student-t (df 4) tails, inverse-vol weights, cash elsewhere, 10-session horizon, daily-close drawdowns. Run 2026-10-06 with the code below (numpy, seed 7):

| Premium | Unconstrained Kelly gross | RCK max gross (α 0.92, β 0.10, λ 27.6, infinite horizon) | E log W₁₀ at gross 0.2 / 0.4 / 0.6 / 0.8 | P(10-session drawdown > 5%) at 0.4 / 0.6 / 0.8 |
|---|---|---|---|---|
| 0%/yr | 0 | 0 | −0.9 / −2.8 / −9.4 / −14.7 bp | 2.9% / 11.4% / 21.1% |
| 6%/yr | 0.63 | 0.044 | +4.7 / +9.6 / +10.3 / +11.0 bp | 2.7% / 10.6% / 19.8% |
| 12%/yr | 1.00 | 0.117 | +11.0 / +21.2 / +28.7 / +34.3 bp | 2.5% / 9.8% / 18.5% |

Finite-horizon maximum gross at a 6%/yr premium, subject to P(10-session drawdown below α) ≤ β: α 0.95, β 0.10 → 0.55; α 0.95, β 0.05 → 0.45; α 0.92, β 0.05 → 0.75; α 0.92, β 0.01 → 0.50.

Readings [INFERENCE from synthetic inputs]:
- Drawdown probabilities barely depend on the premium; expected growth depends on it entirely. Over 10 sessions, the premium sets *whether* to be invested and the drawdown target sets *how much*.
- Expected log growth flattens above ≈ 0.4–0.6 gross while drawdown risk keeps rising, so the efficient region is roughly 0.4–0.6 gross for these assumptions. The declared I-61 sizing (≈ 36–38% gross) sits just below it; the 8% drawdown halt (G-22) would rarely trigger (consistent with I-62).
- The money at stake is small either way (≈ 10 bp of expected log growth at a 6% premium): exposure × market path still dominates the score.
- Tokens trade 24/7 and the organisers' drawdown sampling is unknown (Q-11, Q-39); intraday and weekend excursions make real drawdown risk higher than these daily-close figures.

## 4. Proposed use (for the team to accept or amend)
1. **Inputs, pre-registered:** expected return = β·(equity-premium prior) for every name, with the prior fixed in advance (e.g. [6]%/yr) and no fitted alpha; risk from a block bootstrap of the four US names' daily returns on pre-2025 data (IDEA-004 §3 leak note), scaled to current vol (I-61/I-66); the drawdown target (α, β) chosen by the team as its risk appetite under F-115.
2. **Problem:** at each scheduled rebalance, choose weights b ≥ 0 (cash included) to maximise E log W_T over the remaining run, subject to P(min W over the run < α) ≤ β estimated on the bootstrap scenarios, the G-21 caps (≤ 4 positions, ≤ 20% per name, ≤ 80% gross) and the G-22 halts. With inverse-vol weights it is a one-dimensional search over gross; a full CVXPY solve of the RCK form on scenarios is the cross-check.
3. **Overlay:** vetoes and exits (IDEA-004 §3, each evaluated per IDEA-005 R4) remove names from the feasible set; they never increase exposure.
4. **Costs:** subtract measured round-trip cost (T10) from each rebalance's expected gain and skip rebalances smaller than the cost; RCK itself ignores costs.
5. **Logging:** each round logs α, β, the premium prior, scenario hash, chosen gross and weights, and the estimated drawdown probability, so the sizing is traceable (F-115: logs and repo are assessed).
6. **Declarations:** the proposal declared the I-61 sizing formula; replacing it is a version event with a stated reason before the v1.0 freeze (G-11). Using RCK only to pick parameters inside the declared caps is the lighter option.

## 5. Open questions and limits
- The return prior is a judgement; record it once and never refit it on test data (IDEA-004 §1).
- Log-growth maximisation is not the same as maximising the chance of a top-3 finish (F-02, F-04); the organisers' composite scoring (F-115, Q-39) is not yet specified.
- iid bootstrap ignores volatility clustering; use regime-conditional or recent-window scenarios and report the sensitivity.
- The four names are close to one factor; diversification within the book is limited (IDEA-004 §3).

## 6. Code used for §3
```python
"""Illustrative RCK vs finite-horizon drawdown sizing for a C1-like basket.
All parameters are ASSUMPTIONS for illustration (no market data used)."""
import numpy as np

rng = np.random.default_rng(7)
vol = np.array([0.018, 0.020, 0.030, 0.038])   # daily vol MSFT, GOOGL, NVDA, TSLA [assumed]
beta = np.array([1.0, 1.05, 1.5, 1.8])        # market beta [assumed]
rho, df = 0.55, 4                              # pairwise correlation, Student-t tails [assumed]
C = rho * np.ones((4, 4)) + (1 - rho) * np.eye(4)
L = np.linalg.cholesky(C)
w = (1 / vol) / (1 / vol).sum()                # inverse-vol basket, sums to 1

def daily(n, prem):
    z = rng.standard_normal((n, 4)) @ L.T
    chi = rng.chisquare(df, (n, 1)) / df
    t = z / np.sqrt(chi) * np.sqrt((df - 2) / df)  # unit-variance t
    return np.maximum(beta * prem / 252 + vol * t, -0.5)  # daily simple returns, floored at -50%

def finite(prem, g, T=10, n=100_000):
    r = daily(n * T, prem).reshape(n, T, 4) @ w * g
    W = np.cumprod(1 + r, axis=1)
    Wmin = np.minimum(W.min(axis=1), 1.0)
    return np.log(W[:, -1]).mean(), [(Wmin < a).mean() for a in (0.95, 0.92, 0.88)]

def rck_max_gross(prem, alpha, beta_p, n=400_000):
    lam = np.log(beta_p) / np.log(alpha)
    r = daily(n, prem) @ w
    lo, hi = 0.0, 1.0
    for _ in range(40):
        g = (lo + hi) / 2
        (lo, hi) = (g, hi) if np.mean((1 + g * r) ** (-lam)) <= 1 else (lo, g)
    kelly = max(0.0, min(1.0, r.mean() / r.var()))
    return lam, lo, kelly

print("basket daily vol ~", round(float(np.sqrt(w @ (np.outer(vol, vol) * C) @ w)), 4))
for prem in (0.0, 0.06, 0.12):
    lam, g_rck, kelly = rck_max_gross(prem, alpha=0.92, beta_p=0.10)
    print(f"\nequity premium {prem:.0%}/yr: unconstrained Kelly gross ~{kelly:.2f}; "
          f"RCK (alpha=0.92, beta=0.10, lambda={lam:.1f}, infinite horizon) max gross {g_rck:.3f}")
    for g in (0.2, 0.4, 0.6, 0.8):
        el, p = finite(prem, g)
        print(f"  gross {g:.1f}: E log W_10 = {el*1e4:+.1f} bp; P(min W<0.95/0.92/0.88 within 10 sessions) = "
              + "/".join(f"{x:.3f}" for x in p))

def finite_max_gross(prem, alpha, beta_p):
    best = 0.0
    for g in np.arange(0.05, 1.0001, 0.05):
        if finite(prem, g, n=60_000)[1][(0.95, 0.92, 0.88).index(alpha)] <= beta_p:
            best = g
    return best

print("\nfinite-horizon (10 sessions) max gross s.t. P(min W < alpha) <= beta, premium 6%/yr:")
for a, b in ((0.95, 0.10), (0.95, 0.05), (0.92, 0.05), (0.92, 0.01)):
    print(f"  alpha={a}, beta={b}: max gross {finite_max_gross(0.06, a, b):.2f}")
```
