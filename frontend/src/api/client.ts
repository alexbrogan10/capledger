import type {
  ContractListItem,
  Dashboard,
  Meta,
  PlayerContractProfile,
  PlayerListItem,
  PositionSpending,
  ReleaseImpact,
  RestructureImpact,
  RosterRow,
  Team,
  TeamCap,
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
};
