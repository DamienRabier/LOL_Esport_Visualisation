import { useRefresh } from "../refresh";

// Compact sidebar chip; polling + list reload live in RefreshProvider.
export default function RefreshStatus() {
  const { status, trigger } = useRefresh();
  if (!status) return null;

  const { running, current, done, finished_at, errors } = status;

  return (
    <div className="refresh">
      {running ? (
        <div className="refresh-line">
          <span className="spinner" />
          <span className="refresh-text">
            Updating data
            {current ? ` (${current.index}/${current.total})` : "…"}
            {current?.name ? <span className="refresh-sub">{current.name}</span> : null}
          </span>
        </div>
      ) : (
        <button className="refresh-btn" onClick={trigger} title="Refresh tracked leagues now">
          <span className="refresh-ico">⟳</span>
          {finished_at ? `Updated ${when(finished_at)}` : "Refresh data"}
        </button>
      )}
      {!running && done.length > 0 && (
        <div className="refresh-meta">{done.length} tournaments up to date</div>
      )}
      {errors.length > 0 && (
        <div className="refresh-meta err" title={errors.join("\n")}>
          {errors.length} warning{errors.length > 1 ? "s" : ""}
        </div>
      )}
    </div>
  );
}

function when(iso: string): string {
  const d = new Date(iso);
  const mins = Math.round((Date.now() - d.getTime()) / 60000);
  if (mins < 1) return "just now";
  if (mins < 60) return `${mins}m ago`;
  const h = Math.round(mins / 60);
  if (h < 24) return `${h}h ago`;
  return d.toLocaleDateString();
}
