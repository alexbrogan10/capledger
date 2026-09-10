# Limitations

Cap Ledger is an independent, portfolio analytical project. It is **not**
affiliated with the NFL, the NFLPA, or any NFL team, does not claim access to
proprietary team information, and is not a substitute for professional
contract, financial, or legal advice.

## Data

- The shipped dataset is entirely synthetic (see `docs/data_sources.md`).
  Player identities, ages, and every dollar figure are generated, not real.
- League salary-cap figures used by the demo (`app/seed/demo_data.py`) are a
  synthetic assumption, not the officially reported NFL cap.

## Cap-mechanics simplifications

The cap engine (`docs/cap_engine.md`) intentionally does not model:

- **Void years** (contract years added purely to spread cap charges further).
- **Split contracts** (reduced salary while on injured reserve).
- **LTBE vs. NLTBE incentive** distinctions — all incentives are treated as a
  flat cap addition, not conditionally likely/unlikely to be earned.
- **Offset language** in dead-cap calculations after a release.
- **Option bonuses** as a distinct structure (modeled, if at all, as
  additional signing-bonus-style proration).
- **Rookie-scale contract rules** (fifth-year options, proven-performance
  escalators) — rookie contracts in the demo dataset are generated with the
  same generic structure as veteran deals.
- **Practice-squad and minimum-salary-benefit accounting nuances.**

These are simplifications of real, more intricate CBA mechanics, chosen to
keep the engine transparent and auditable. They are documented assumptions,
not a claim of precise or proprietary NFL accounting.

## Analytical outputs

- "Decision points" identified on a player's contract timeline (expiration,
  large cap-hit years, potential release points, possible extension windows)
  are **analytical flags**, not predictions of what any team intends to do.
- The Release Calculator and Restructure Simulator are **hypothetical
  scenario tools**. They do not mutate any stored contract or roster data.
- Cap Ledger does not label any contract as objectively "good" or "bad," or
  any transaction as automatically beneficial — it reports the tradeoffs and
  lets the user apply their own criteria and competitive context.

## Scope not yet built

This repository implements Phase 1 of the roadmap described in the project
brief. Financial Flexibility scoring, contract efficiency/risk models,
historical-contract comparisons, free-agent/rookie planning, sensitivity
analysis, and ML-driven components are reserved for later phases and are not
present in this version. See `docs/architecture.md` for the current scope.
