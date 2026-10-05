# LARP — Strategy opinions (S)

> Contest-strategy views (tournament incentives, crowding, tie-breaks, where LARP sits). **Not evidence of proposal quality; keep out of the proposal. Revisit before final activation (Oct 27–29).**
> IDs are stable; see `SKILL.md` for the reading contract and label meanings.
> Split out of SKILL.md v0.3 on 2026-09-30 (v0.4 restructure); item wording unchanged except the v0.4 fixes listed in SKILL.md Appendix B.

## APPENDIX A — STRATEGY OPINIONS (S). Not evidence of proposal quality; keep out of the proposal.

These concern how to *place* in a raw-return contest. They do not bear on the Stage 1 rubric. Revisit before final activation, once the opening asset, valuation and instrument list are known.

- **S-01 (was I-02) The prize structure rewards variance.** Top 3 of ≤25 paid (F-02, F-04), raw return (F-43), no own capital at risk (F-25). Theory (L-41, L-42, L-43): with p ≈ 0.12, bounded, positively skewed, low-correlation risk raises P(top 3). Counterpoints: no live leaderboard (F-19) prevents rank-conditioning; weekly diagnostics may act as a delayed one (F-51, Q-21); Busse (L-40) finds tournament effects weaker in daily data; the Seeds recruitment prize rewards a sound system regardless of rank (E-20); a large variance increase contradicts a conservative declared design (I-35). Example [ESTIMATE, our Monte Carlo]: 25 teams with zero-mean normal returns and pairwise correlation 0, 0.5 or 0.8; one team scales its whole return by 2 (e.g., doubles exposure). Its P(top 3) rises from ≈12% to ≈27%, 29% and 33% respectively. Caveats: assumes zero expected return for everyone and ignores costs; the same scaling doubles the chance of finishing near the bottom; with a negative expected edge after costs the gain shrinks.
- **S-02 (was I-10) Crowding.** Up to 25 agents may trade the same thin pools and names, compounding slippage near events. Counterpoint: size of the effect unknown; spreads may be deep enough for small wallets.
- **S-03 (was I-11) Tie-breaks rarely matter** except among near-flat teams; don't give up expected return merely to protect drawdown. Counterpoint: if many teams stay flat in a falling market, drawdown decides among them (F-45).
- **S-04 (was P-02) Avoid the middle.** A diversified, always-invested book ranks near the pack. Counterpoint: "the middle" is also the most defensible posture for the audit and for recruitment.
- **S-05 (was P-03) Exposure before selection** over 14 days (see I-05).
- **S-06 (was P-04) Be different on purpose** (lower correlation to the field). Counterpoint: "different" without edge is just noise.
- **S-07 Where LARP sits.** LARP's draft (T-14, I-61) behaves like a hold-heavy book: it is likely to rank well if markets fall and poorly if they rise sharply. That is a legitimate choice (formerly decision D-01, retired with the proposal; git 2985af5); it should be made knowingly, not by accident.
