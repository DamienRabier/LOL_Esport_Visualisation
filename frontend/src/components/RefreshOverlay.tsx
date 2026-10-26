import { useEffect, useState } from "react";
import { useRefresh } from "../refresh";
import { useTournaments } from "../store";

// Full-screen progress interface shown while the launch refresh runs. Blocks the
// app on a first run (no data yet); dismissible once there's data to browse.
export default function RefreshOverlay() {
  const { status } = useRefresh();
  const { tournaments } = useTournaments();
  const [dismissed, setDismissed] = useState(false);

  // Reset the dismissal whenever a new refresh run starts.
  const runId = status?.started_at ?? null;
  useEffect(() => {
    setDismissed(false);
  }, [runId]);

  // Ticking elapsed timer so the user sees the process is alive.
  const [, tick] = useState(0);
  useEffect(() => {
    if (!status?.running) return;
    const t = setInterval(() => tick((n) => n + 1), 1000);
    return () => clearInterval(t);
  }, [status?.running]);

  if (!status?.running || dismissed) return null;

  const hasData = tournaments.length > 0;
  const total = status.total;
  const doneN = status.done.length;
  const pct = total ? Math.round((100 * doneN) / total) : 0;
  const recent = [...status.done].reverse().slice(0, 8);
  const elapsed = status.started_at
    ? Math.max(0, Math.round((Date.now() - new Date(status.started_at).getTime()) / 1000))
    : 0;
  const mmss = `${Math.floor(elapsed / 60)}:${String(elapsed % 60).padStart(2, "0")}`;

  return (
    <div className="overlay">
      <div className="overlay-card">
        <div className="overlay-head">
          <span className="spinner big" />
          <div>
            <h2>Updating data</h2>
            <p className="muted">{status.phase ?? "Refreshing tracked leagues from Leaguepedia…"}</p>
          </div>
          <span className="overlay-timer">{mmss}</span>
        </div>

        <div className={`progress${total ? "" : " indeterminate"}`}>
          <div className="progress-bar" style={total ? { width: `${pct}%` } : undefined} />
        </div>
        <div className="progress-meta">
          {total
            ? `${doneN} / ${total} tournaments`
            : (status.phase ?? "Preparing…")}
          {status.skipped ? <span className="muted"> · {status.skipped} finished (skipped)</span> : null}
          {status.current?.name ? (
            <span className="progress-current"> · fetching {status.current.name}</span>
          ) : null}
        </div>

        {recent.length > 0 && (
          <ul className="overlay-list">
            {recent.map((d, i) => (
              <li key={i}>
                <span className="ok">✓</span>
                <span className="nm">{d.name}</span>
                <span className="ct">{d.counts?.Games ?? 0} games</span>
              </li>
            ))}
          </ul>
        )}

        {status.oe && (
          <div className="muted small">
            Oracle&apos;s Elixir {status.oe.year}:{" "}
            {status.oe.reloaded
              ? `updated (${status.oe.rows.toLocaleString()} rows)`
              : status.oe.error
                ? "using cached file (download quota)"
                : "up to date"}
          </div>
        )}

        {status.errors.length > 0 && (
          <div className="overlay-warn" title={status.errors.join("\n")}>
            {status.errors.length} warning{status.errors.length > 1 ? "s" : ""} (click-hover for details)
          </div>
        )}

        {hasData ? (
          <button className="btn primary overlay-continue" onClick={() => setDismissed(true)}>
            Continue to app →
          </button>
        ) : (
          <p className="muted small">This can take a couple of minutes on first load.</p>
        )}
      </div>
    </div>
  );
}
