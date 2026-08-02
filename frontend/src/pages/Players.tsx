import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { api, type Row } from "../api";
import { useAsync } from "../hooks";
import { useTournaments } from "../store";
import { Loader } from "../components/ui";

interface Col {
  key: string;
  label: string;
  pct?: boolean;
  diff?: boolean;
  fmt?: (v: any) => string;
}

const COLS: Col[] = [
  { key: "player", label: "Player" },
  { key: "team", label: "Team" },
  { key: "role", label: "Role" },
  { key: "games", label: "G" },
  { key: "record", label: "K/D/A" },
  { key: "kda", label: "KDA" },
  { key: "winrate", label: "Win%", pct: true },
  { key: "cs", label: "Avg CS" },
  { key: "dpm", label: "DPM", fmt: (v) => Number(v).toLocaleString() },
  { key: "GD@15", label: "GD@15", diff: true },
];

const ROLES = ["All", "Top", "Jungle", "Mid", "Bot", "Support"];

export default function Players() {
  const { selected } = useTournaments();
  const nav = useNavigate();
  const op = selected?.overviewpage ?? "";
  const { data, error, loading } = useAsync(() => api.playersLeaderboard(op), [op]);
  const [sortKey, setSortKey] = useState("winrate");
  const [asc, setAsc] = useState(false);
  const [role, setRole] = useState("All");

  if (loading || error) return <Loader error={error} loading={loading} />;
  if (!data || data.length === 0) return <div className="empty">No players for this tournament.</div>;

  const filtered = role === "All" ? data : data.filter((r) => r.role === role);
  const rows = [...filtered].sort((a, b) => {
    const av = a[sortKey], bv = b[sortKey];
    if (av == null) return 1;
    if (bv == null) return -1;
    if (typeof av === "number" && typeof bv === "number") return asc ? av - bv : bv - av;
    return asc ? String(av).localeCompare(String(bv)) : String(bv).localeCompare(String(av));
  });

  const click = (key: string) => {
    if (key === sortKey) setAsc(!asc);
    else { setSortKey(key); setAsc(key === "player" || key === "team" || key === "role"); }
  };

  const cell = (c: Col, r: Row) => {
    if (c.key === "record") return `${r.k}/${r.d}/${r.a}`;
    const v = r[c.key];
    if (v == null) return <span className="muted">—</span>;
    if (c.pct && typeof v === "number")
      return <span className={v > 50 ? "pct-good" : v < 50 ? "pct-bad" : ""}>{v}%</span>;
    if (c.diff && typeof v === "number")
      return <span className={v > 0 ? "pct-good" : v < 0 ? "pct-bad" : ""}>{v > 0 ? `+${v}` : v}</span>;
    return c.fmt ? c.fmt(v) : String(v);
  };

  return (
    <div className="page">
      <h2>🧑 Players</h2>
      <div className="row">
        <p className="muted" style={{ flex: 1, margin: 0 }}>
          All players in <strong>{selected?.name}</strong> — click a player for their detail page.
        </p>
        <select className="select" value={role} onChange={(e) => setRole(e.target.value)}>
          {ROLES.map((r) => <option key={r}>{r}</option>)}
        </select>
      </div>
      <div className="table-wrap">
        <table>
          <thead>
            <tr>
              {COLS.map((c) => (
                <th
                  key={c.key}
                  className={`sortable${["player", "team", "role"].includes(c.key) ? "" : " num"}${sortKey === c.key ? " sorted" : ""}`}
                  onClick={() => click(c.key)}
                >
                  {c.label}{sortKey === c.key ? (asc ? " ▲" : " ▼") : ""}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.map((r, i) => (
              <tr key={i} className="clickable"
                onClick={() => nav(`/player?player=${encodeURIComponent(r.player)}&team=${encodeURIComponent(r.team)}`)}>
                {COLS.map((c) => (
                  <td key={c.key} className={["player", "team", "role"].includes(c.key) ? (c.key === "player" ? "team-cell" : "") : "num"}>
                    {cell(c, r)}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
