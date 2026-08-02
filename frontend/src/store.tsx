import { createContext, useContext, useEffect, useMemo, useState } from "react";
import type { ReactNode } from "react";
import { api, type Tournament } from "./api";

interface TournamentState {
  tournaments: Tournament[];
  loading: boolean;
  error: string | null;
  selected: Tournament | null;
  setSelected: (t: Tournament) => void;
  reload: () => void;
}

const Ctx = createContext<TournamentState | null>(null);

export function TournamentProvider({ children }: { children: ReactNode }) {
  const [tournaments, setTournaments] = useState<Tournament[]>([]);
  const [selected, setSelected] = useState<Tournament | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [nonce, setNonce] = useState(0);

  useEffect(() => {
    let alive = true;
    setLoading(true);
    api
      .tournaments()
      .then((ts) => {
        if (!alive) return;
        setTournaments(ts);
        setSelected((cur) => cur ?? ts[0] ?? null);
      })
      .catch((e) => alive && setError(String(e.message || e)))
      .finally(() => alive && setLoading(false));
    return () => {
      alive = false;
    };
  }, [nonce]);

  const value = useMemo(
    () => ({
      tournaments,
      loading,
      error,
      selected,
      setSelected,
      reload: () => setNonce((n) => n + 1),
    }),
    [tournaments, loading, error, selected],
  );

  return <Ctx.Provider value={value}>{children}</Ctx.Provider>;
}

export function useTournaments() {
  const ctx = useContext(Ctx);
  if (!ctx) throw new Error("useTournaments must be used within TournamentProvider");
  return ctx;
}
