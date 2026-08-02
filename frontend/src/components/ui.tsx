import type { ReactNode } from "react";
import type { Row } from "../api";

export function Metric({ label, value, sub }: { label: string; value: ReactNode; sub?: ReactNode }) {
  return (
    <div className="metric">
      <div className="metric-label">{label}</div>
      <div className="metric-value">{value ?? "—"}</div>
      {sub != null && <div className="metric-sub">{sub}</div>}
    </div>
  );
}

export function Loader({ error, loading }: { error?: string | null; loading?: boolean }) {
  if (error) return <div className="error">⚠ {error}</div>;
  if (loading) return <div className="loader">Loading…</div>;
  return null;
}

const WIN_COLS = new Set(["win", "playerwin", "winner"]);

export function DataTable({
  rows,
  columns,
  pctColumns,
  hideColumns,
  onRowClick,
  matchColumn,
  matchValue,
}: {
  rows: Row[];
  columns?: string[];
  // Columns whose numeric % is coloured red (<50) / blue (>50).
  pctColumns?: string[];
  hideColumns?: string[];
  onRowClick?: (row: Row) => void;
  // In `matchColumn`, colour the cell blue when it equals `matchValue`, else red.
  matchColumn?: string;
  matchValue?: string;
}) {
  if (!rows || rows.length === 0) return <div className="empty">No data.</div>;
  const hide = new Set(hideColumns ?? []);
  const cols = (columns ?? Object.keys(rows[0])).filter((c) => !hide.has(c));
  const pct = new Set(pctColumns ?? []);

  // A column is numeric if every non-null value in it is a number.
  const numericCols = new Set(
    cols.filter((c) => rows.every((r) => r[c] == null || typeof r[c] === "number")),
  );

  return (
    <div className="table-wrap">
      <table>
        <thead>
          <tr>
            {cols.map((c) => (
              <th key={c} className={numericCols.has(c) ? "num" : undefined}>
                {c}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((r, i) => (
            <tr
              key={i}
              className={onRowClick ? "clickable" : undefined}
              onClick={onRowClick ? () => onRowClick(r) : undefined}
            >
              {cols.map((c) => (
                <td key={c} className={numericCols.has(c) ? "num" : undefined}>
                  {c === matchColumn && r[c] != null && r[c] !== "" ? (
                    <span className={r[c] === matchValue ? "pct-good" : "pct-bad"}>{r[c]}</span>
                  ) : (
                    renderCell(c, r[c], pct.has(c))
                  )}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function renderCell(col: string, v: any, isPct = false): ReactNode {
  if (v == null || v === "") return "";
  if (isPct && typeof v === "number") {
    const cls = v > 50 ? "pct-good" : v < 50 ? "pct-bad" : undefined;
    return <span className={cls}>{v}</span>;
  }
  if (WIN_COLS.has(col.toLowerCase()) && (v === "Yes" || v === "No")) {
    return <span className={`badge ${v === "Yes" ? "win" : "loss"}`}>{v === "Yes" ? "Win" : "Loss"}</span>;
  }
  if (Array.isArray(v)) return v.join(", ");
  if (typeof v === "number") {
    // Large counts get thousands separators; keep small/decimals as-is.
    return Number.isInteger(v) && Math.abs(v) >= 1000 ? v.toLocaleString() : String(v);
  }
  if (typeof v === "string" && v.length >= 19 && v.includes("T")) {
    const d = new Date(v);
    if (!isNaN(d.getTime())) return d.toISOString().slice(0, 10);
  }
  return String(v);
}
