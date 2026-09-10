# Contract Methodology

How Cap Ledger structures and stores a contract (see `backend/app/models/contract.py`
and `contract_year.py`).

## Contract-level fields

- `total_value` — sum of all base salaries across the contract's years plus
  the signing bonus (i.e., total new money over the life of the deal).
- `annual_value` (AAV) — `total_value / years`. The standard way to compare
  contracts of different lengths.
- `guaranteed_money` — the portion of `total_value` the team owes regardless
  of release. In the demo generator, this is signing bonus (always
  guaranteed) plus guaranteed base salary in the earliest contract year(s).
- `signing_bonus` — paid up front, recognized on the cap via proration (see
  `docs/cap_engine.md`).
- `current_salary` / `current_cap_hit` — convenience caches of the contract's
  current-season `ContractYear` row. `ContractYear` is always the source of
  truth; these two columns exist so simple list views don't need a join.

## Year-level fields (`ContractYear`)

Each season of a contract has its own row with `base_salary`,
`signing_bonus_proration`, `roster_bonus`, `incentives`, the computed
`cap_hit`, `cash_value` (money actually paid that year), `dead_cap_value`
(populated only for released/traded contracts — the realized dead-cap charge
for that season), and `guaranteed_base_salary` (the subset of that season's
base salary that is guaranteed).

## Contract status

`active`, `released`, `traded`, `expired`, `void`. The Roster Ledger and
Contract Explorer default to `active` contracts; released contracts remain in
the database (with zeroed future cap hits and populated dead-cap rows) so
historical dead-cap reporting stays accurate.
