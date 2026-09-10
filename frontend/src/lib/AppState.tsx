import { createContext, useContext, useEffect, useMemo, useState, type ReactNode } from "react";
import { api } from "../api/client";
import type { Meta, Team } from "../api/types";

interface AppStateValue {
  teams: Team[];
  meta: Meta | null;
  selectedTeamId: number | null;
  setSelectedTeamId: (id: number) => void;
  season: number;
  setSeason: (season: number) => void;
  loading: boolean;
}

const AppStateContext = createContext<AppStateValue | null>(null);

export function AppStateProvider({ children }: { children: ReactNode }) {
  const [teams, setTeams] = useState<Team[]>([]);
  const [meta, setMeta] = useState<Meta | null>(null);
  const [selectedTeamId, setSelectedTeamId] = useState<number | null>(null);
  const [season, setSeason] = useState<number>(2026);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([api.teams(), api.meta()]).then(([teamsResp, metaResp]) => {
      setTeams(teamsResp);
      setMeta(metaResp);
      setSeason(metaResp.current_season);
      const stored = localStorage.getItem("capledger.selectedTeamId");
      const initial = stored ? Number(stored) : teamsResp[0]?.id ?? null;
      setSelectedTeamId(initial);
      setLoading(false);
    });
  }, []);

  const handleSetTeam = (id: number) => {
    setSelectedTeamId(id);
    localStorage.setItem("capledger.selectedTeamId", String(id));
  };

  const value = useMemo(
    () => ({
      teams,
      meta,
      selectedTeamId,
      setSelectedTeamId: handleSetTeam,
      season,
      setSeason,
      loading,
    }),
    [teams, meta, selectedTeamId, season, loading]
  );

  return <AppStateContext.Provider value={value}>{children}</AppStateContext.Provider>;
}

export function useAppState(): AppStateValue {
  const ctx = useContext(AppStateContext);
  if (!ctx) throw new Error("useAppState must be used within AppStateProvider");
  return ctx;
}
