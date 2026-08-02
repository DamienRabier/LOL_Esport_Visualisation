import { createContext, useContext, useEffect, useRef, useState } from "react";
import type { ReactNode } from "react";
import { api, type RefreshStatus } from "./api";
import { useTournaments } from "./store";

interface RefreshCtx {
  status: RefreshStatus | null;
  trigger: () => Promise<void>;
}

const Ctx = createContext<RefreshCtx | null>(null);

// Polls the backend's auto-refresh status once for the whole app and reloads the
// tournament list when a refresh finishes. Consumed by both the sidebar chip and
// the load-time progress overlay.
export function RefreshProvider({ children }: { children: ReactNode }) {
  const { reload } = useTournaments();
  const [status, setStatus] = useState<RefreshStatus | null>(null);
  const wasRunning = useRef(false);

  useEffect(() => {
    let alive = true;
    let timer: ReturnType<typeof setTimeout>;
    const poll = async () => {
      try {
        const s = await api.refreshStatus();
        if (!alive) return;
        setStatus(s);
        if (wasRunning.current && !s.running) reload(); // finished -> refresh list
        wasRunning.current = s.running;
        timer = setTimeout(poll, s.running ? 2000 : 20000);
      } catch {
        if (alive) timer = setTimeout(poll, 15000);
      }
    };
    poll();
    return () => {
      alive = false;
      clearTimeout(timer);
    };
  }, [reload]);

  const trigger = async () => {
    try {
      await api.startRefresh();
      setStatus((s) => (s ? { ...s, running: true, done: [], errors: [], total: 0, current: null } : s));
      wasRunning.current = true;
    } catch {
      /* ignore */
    }
  };

  return <Ctx.Provider value={{ status, trigger }}>{children}</Ctx.Provider>;
}

export function useRefresh() {
  const ctx = useContext(Ctx);
  if (!ctx) throw new Error("useRefresh must be used within RefreshProvider");
  return ctx;
}
