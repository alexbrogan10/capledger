import type {
  CapProjection,
  ComparableContracts,
  Concentration,
  ContractListItem,
  ContractRisk,
  ContractValue,
  ContractValueProjection,
  Dashboard,
  DeadCapDashboard,
  ExtensionImpact,
  FinancialFlexibility,
  FlexibilityForecast,
  FreeAgentPlanning,
  Meta,
  PlayerContractProfile,
  PlayerListItem,
  PositionSpending,
  PositionSpendingComparison,
  ReleaseImpact,
  RestructureImpact,
  RookiePlanning,
  RosterRow,
  ScenarioComparison,
  Team,
  TeamCap,
  TradeImpact,
} from "./types";

const BASE = "/api";

async function get<T>(path: string, params?: Record<string, string | number | boolean | undefined>): Promise<T> {
  const url = new URL(BASE + path, window.location.origin);
  if (params) {
    for (const [key, value] of Object.entries(params)) {
      if (value !== undefined && value !== null) url.searchParams.set(key, String(value));
    }
  }
  const resp = await fetch(url.toString().replace(window.location.origin, ""));
  if (!resp.ok) {
    const body = await resp.text();
    throw new Error(`Request failed (${resp.status}): ${body}`);
  }
  return resp.json();
}

async function post<T>(path: string, body: unknown): Promise<T> {
  const resp = await fetch(BASE + path, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!resp.ok) {
    const errBody = await resp.text();
    throw new Error(`Request failed (${resp.status}): ${errBody}`);
  }
  return resp.json();
}

export const api = {
  meta: () => get<Meta>("/meta"),
  teams: () => get<Team[]>("/teams"),
  team: (id: number) => get<Team>(`/teams/${id}`),
  teamCap: (id: number, season: number) => get<TeamCap>(`/teams/${id}/cap`, { season }),
  teamRoster: (id: number, season: number) => get<RosterRow[]>(`/teams/${id}/roster`, { season }),
  teamSpending: (id: number, season: number) => get<PositionSpending[]>(`/teams/${id}/spending`, { season }),
  dashboard: (id: number, season: number) => get<Dashboard>(`/teams/${id}/dashboard`, { season }),

  players: (params: { team_id?: number; position?: string; search?: string; season?: number }) =>
    get<PlayerListItem[]>("/players", params),
  playerProfile: (id: number) => get<PlayerContractProfile>(`/players/${id}`),

  contracts: (params: {
    team_id?: number;
    position?: string;
    search?: string;
    min_aav?: number;
    max_aav?: number;
    min_guaranteed?: number;
    contract_status?: string;
    season?: number;
  }) => get<ContractListItem[]>("/contracts", params),

  simulateRelease: (contractId: number, release_season: number, june1: boolean) =>
    post<ReleaseImpact>(`/contracts/${contractId}/release`, { release_season, june1 }),

  simulateRestructure: (contractId: number, restructure_season: number, amount_to_convert: number) =>
    post<RestructureImpact>(`/contracts/${contractId}/restructure`, { restructure_season, amount_to_convert }),

  simulateTrade: (contractId: number, trade_season: number) =>
    post<TradeImpact>(`/contracts/${contractId}/trade`, { trade_season }),

  simulateExtension: (
    contractId: number,
    body: {
      extension_start_season: number;
      new_length_years: number;
      new_total_value: number;
      new_signing_bonus: number;
      new_guaranteed_money: number;
    }
  ) => post<ExtensionImpact>(`/contracts/${contractId}/extend`, body),

  scenarioComparison: (contractId: number, season: number) =>
    get<ScenarioComparison>(`/contracts/${contractId}/scenarios`, { season }),

  recomputeProjections: (teamId: number, growth_rate: number, seasons?: number[]) =>
    post<CapProjection>(`/teams/${teamId}/projections`, { growth_rate, seasons }),

  deadCapDashboard: (teamId: number, season: number) =>
    get<DeadCapDashboard>(`/teams/${teamId}/dead-cap`, { season }),

  financialFlexibility: (teamId: number, season: number, weights?: Record<string, number>) =>
    get<FinancialFlexibility>("/analytics/financial-flexibility", {
      team_id: teamId,
      season,
      ...(weights
        ? Object.fromEntries(Object.entries(weights).map(([k, v]) => [`w_${k}`, v]))
        : {}),
    }),

  concentration: (teamId: number, season: number) =>
    get<Concentration>("/analytics/concentration", { team_id: teamId, season }),

  contractRisk: (contractId: number, season: number) =>
    get<ContractRisk>("/analytics/contract-risk", { contract_id: contractId, season }),

  contractValue: (contractId: number) =>
    get<ContractValue>("/analytics/contract-value", { contract_id: contractId }),

  positionSpendingComparison: (teamId: number, season: number) =>
    get<PositionSpendingComparison>("/analytics/position-spending-comparison", { team_id: teamId, season }),

  flexibilityForecast: (teamId: number, growthRate: number, sensitivityDelta?: number) =>
    get<FlexibilityForecast>(`/teams/${teamId}/financial-flexibility-forecast`, {
      growth_rate: growthRate,
      sensitivity_delta: sensitivityDelta,
    }),

  freeAgentPlanning: (
    teamId: number,
    body: { position: string; target_aav: number; contract_length: number; guaranteed_money: number; start_season: number }
  ) => post<FreeAgentPlanning>(`/teams/${teamId}/free-agent-planning`, body),

  rookiePlanning: (teamId: number, season: number, picks: { draft_round: number; position?: string }[]) =>
    post<RookiePlanning>(`/teams/${teamId}/rookie-planning`, { season, picks }),

  contractValueProjection: (position: string, age: number, contractLengthYears: number) =>
    get<ContractValueProjection>("/ml/contract-value-projection", {
      position, age, contract_length_years: contractLengthYears,
    }),

  comparableContracts: (position: string, age: number, aav: number, limit = 10) =>
    get<ComparableContracts>("/analytics/comparable-contracts", { position, age, aav, limit }),
};
