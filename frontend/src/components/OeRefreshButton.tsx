import { useEffect, useRef, useState } from "react";
import { api, type OeResult } from "../api";

// Triggers an on-demand Oracle's Elixir refresh (download attempt + reload if
// the file changed) and shows the outcome. Polls while running.
export default function OeRefreshButton({ onDone }: { onDone?: () => void }) {
  const [running, setRunning] = useState(false);
  const [msg, setMsg] = useState<string | null>(null);
  const poll = useRef<ReturnType<typeof setTimeout>>();

  useEffect(() => () => clearTimeout(poll.current), []);

  const describe = (r: OeResult | null): string => {
    if (!r) return "";
    if (r.reloaded) return `Updated — ${r.rows.toLocaleString()} rows`;
    if (r.error) return "Download blocked (quota) — using cached";
    return "Already up to date";
  };

  const check = async () => {
    try {
      const s = await api.oeRefreshStatus();
      if (s.running) {
        poll.current = setTimeout(check, 2000);
      } else {
        setRunning(false);
        setMsg(describe(s.result));
        onDone?.();
      }
    } catch {
      setRunning(false);
      setMsg("Refresh failed");
    }
  };

  const start = async () => {
    setRunning(true);
    setMsg(null);
    try {
      await api.oeRefresh();
      poll.current = setTimeout(check, 1500);
    } catch {
      setRunning(false);
      setMsg("Could not start");
    }
  };

  return (
    <div className="oe-refresh">
      <button className="btn" onClick={start} disabled={running}>
        {running ? <span className="spinner" /> : <span className="refresh-ico">⟳</span>}
        {running ? "Updating OE…" : "Update OE data"}
      </button>
      {msg && <span className="muted small">{msg}</span>}
    </div>
  );
}
