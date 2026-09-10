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

export interface TradeImpact {
  player_id: number;
  player_name: string;
  contract_id: number;
  trade_season: number;
  trading_team_id: number;
  trading_team_pre_trade_cap_hit: number;
  trading_team_dead_cap: number;
  trading_team_cap_savings: number;
  acquiring_team_cap_hits: Record<string, number>;
  acquiring_team_total_remaining_commitment: number;
  assumptions: string[];
  scenario_id: number | null;
}

export interface ExtensionYear {
  season: number;
  base_salary: number;
  signing_bonus_proration: number;
  cap_hit: number;
  guaranteed_base_salary: number;
}

export interface ExtensionImpact {
  player_id: number;
  player_name: string;
  contract_id: number;
  extension_start_season: number;
  current_contract_years: ExtensionYear[];
  new_contract_years: ExtensionYear[];
  combined_years: ExtensionYear[];
  total_new_commitment: number;
  total_new_guaranteed: number;
  first_year_cap_hit_change: number;
  assumptions: string[];
  scenario_id: number | null;
}

export interface ScenarioOption {
  scenario_type: string;
  label: string;
  current_year_cap_impact: number;
  future_year_impact: string;
  dead_cap: number;
  assessment: "Strong" | "Favorable" | "Moderate" | "Unfavorable" | "Conditional";
  reasoning: string[];
}

export interface ScenarioComparison {
  player_id: number;
  player_name: string;
  contract_id: number;
  season: number;
  options: ScenarioOption[];
  disclaimer: string;
}

export interface CapProjectionSeason {
  season: number;
  projected_cap: number;
  projected_commitments: number;
  projected_space: number;
}

export interface CapProjection {
  team_id: number;
  base_season: number;
  base_cap: number;
  growth_rate: number;
  run_id: string;
  seasons: CapProjectionSeason[];
  assumptions: string[];
}

export interface DeadCapPlayerRow {
  player_id: number;
  player_name: string;
  position: string;
  season: number;
  dead_cap_value: number;
  contract_status: string;
}

export interface DeadCapSeasonRow {
  season: number;
  dead_cap: number;
}

export interface DeadCapDashboard {
  team_id: number;
  current_season: number;
  total_dead_cap_current_season: number;
  by_player: DeadCapPlayerRow[];
  by_season: DeadCapSeasonRow[];
}

export interface FlexibilityFactor {
  key: string;
  label: string;
  score: number;
  weight: number;
  direction: "+" | "-" | "~";
  detail: string;
}

export interface FinancialFlexibility {
  team_id: number;
  season: number;
  score: number;
  factors: FlexibilityFactor[];
  weights_used: Record<string, number>;
  disclaimer: string;
}

export interface Concentration {
  team_id: number;
  season: number;
  total_commitments: number;
  top1_pct: number;
  top3_pct: number;
  top5_pct: number;
  top10_pct: number;
  top1_dollars: number;
  top3_dollars: number;
  top5_dollars: number;
  top10_dollars: number;
  interpretation: string;
}

export interface RiskFactor {
  label: string;
  contributes_risk: boolean;
  detail: string;
}

export interface ContractRisk {
  contract_id: number;
  player_id: number;
  player_name: string;
  risk_score: number;
  category: "Low" | "Moderate" | "High" | "Very High";
  factors: RiskFactor[];
  disclaimer: string;
}

export interface ContractValue {
  contract_id: number;
  player_id: number;
  player_name: string;
  position: string;
  age: number;
  aav: number;
  position_median_aav: number;
  percentile: number;
  age_band_median_aav: number;
  age_band_percentile: number;
  sample_size: number;
  cost_vs_position_median: number;
  discrepancy_label: string;
  disclaimer: string;
}

export interface PositionSpendingComparisonRow {
  position_group: string;
  team_cap_spending: number;
  team_cap_percentage: number;
  league_avg_cap_percentage: number;
  difference: number;
}

export interface PositionSpendingComparison {
  team_id: number;
  season: number;
  rows: PositionSpendingComparisonRow[];
}

export interface FlexibilityForecastSeason {
  season: number;
  score: number;
  top_positive_factor: string | null;
  top_negative_factor: string | null;
}

export interface FlexibilityForecast {
  team_id: number;
  growth_rate: number;
  seasons: FlexibilityForecastSeason[];
  narrative: string[];
  what_would_change_our_mind: string[];
  disclaimer: string;
}

export interface FreeAgentPlanning {
  team_id: number;
  position: string;
  start_season: number;
  projected_total_value: number;
  projected_signing_bonus: number;
  year_by_year_cap_hit: Record<string, number>;
  cap_space_before: number;
  cap_space_after: number;
  flexibility_score_before: number;
  flexibility_score_after: number;
  assumptions: string[];
}

export interface RookiePickImpact {
  draft_round: number;
  position: string | null;
  total_value: number;
  signing_bonus: number;
  first_year_cap_hit: number;
}

export interface RookiePlanning {
  team_id: number;
  season: number;
  picks: RookiePickImpact[];
  total_first_year_cap_impact: number;
  cap_space_before: number;
  cap_space_after: number;
  assumptions: string[];
}
