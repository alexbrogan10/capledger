export interface Team {
  id: number;
  name: string;
  abbreviation: string;
  conference: string;
  division: string;
}

export interface TeamCap {
  team_id: number;
  season: number;
  salary_cap: number;
  cap_commitments: number;
  top51_commitments: number;
  dead_cap: number;
  cap_space: number;
  effective_cap_space: number;
  definitions: Record<string, string>;
}

export interface PositionSpending {
  position_group: string;
  cap_spending: number;
  cap_percentage: number;
  player_count: number;
}

export interface FinancialAlert {
  severity: "info" | "watch" | "high";
  category: string;
  message: string;
  player_id?: number | null;
  player_name?: string | null;
  season?: number | null;
  amount?: number | null;
}

export interface TopCommitment {
  player_name: string;
  position: string;
  cap_hit: number;
}

export interface Dashboard {
  team: Team;
  season: number;
  current_cap: TeamCap;
  future_cap: TeamCap[];
  position_spending: PositionSpending[];
  alerts: FinancialAlert[];
  top_commitments: TopCommitment[];
}

export interface RosterRow {
  player_id: number;
  player_name: string;
  position: string;
  age: number;
  contract_status: string;
  contract_years_remaining: number;
  annual_value: number;
  current_salary: number;
  current_cap_hit: number;
  guaranteed_money: number;
  dead_cap_if_released: number | null;
  cash_this_year: number;
  pct_of_team_cap: number | null;
}

export interface PlayerListItem {
  id: number;
  name: string;
  position: string;
  team_id: number | null;
  age: number;
  experience: number;
  status: string;
  team_abbreviation: string | null;
  current_cap_hit: number | null;
  years_remaining: number | null;
  contract_status: string | null;
}

export interface ContractYear {
  season: number;
  base_salary: number;
  signing_bonus_proration: number;
  roster_bonus: number;
  incentives: number;
  cap_hit: number;
  cash_value: number;
  dead_cap_value: number;
  guaranteed_base_salary: number;
}

export interface DecisionPoint {
  season: number;
  kind: string;
  label: string;
  detail: string;
}

export interface PlayerContractProfile {
  player: PlayerListItem;
  team_abbreviation: string | null;
  contract_id: number;
  contract_start: number;
  contract_end: number;
  total_value: number;
  annual_value: number;
  guaranteed_money: number;
  signing_bonus: number;
  contract_status: string;
  financial_timeline: ContractYear[];
  decision_points: DecisionPoint[];
}

export interface ContractListItem {
  id: number;
  player_id: number;
  player_name: string;
  position: string;
  team_id: number;
  team_abbreviation: string;
  contract_start: number;
  contract_end: number;
  years_remaining: number;
  annual_value: number;
  guaranteed_money: number;
  current_cap_hit: number;
  contract_status: string;
  age: number;
}

export interface ReleaseImpact {
  player_id: number;
  player_name: string;
  contract_id: number;
  release_season: number;
  june1: boolean;
  before_cap_hit: number;
  after_dead_cap_current_year: number;
  after_dead_cap_next_year: number;
  current_year_cap_savings: number;
  total_dead_cap: number;
  next_year_cap_hit_removed: number;
  team_id: number;
  team_cap_before: number | null;
  team_cap_after: number | null;
  assumptions: string[];
}

export interface RestructureImpact {
  player_id: number;
  player_name: string;
  contract_id: number;
  season: number;
  original_cap_hit: number;
  new_cap_hit: number;
  current_year_savings: number;
  converted_amount: number;
  future_cap_hit_increases: Record<string, number>;
  assumptions: string[];
}

export interface Meta {
  demo_mode: boolean;
  demo_disclaimer: string;
  current_season: number;
  projection_seasons: number[];
}
