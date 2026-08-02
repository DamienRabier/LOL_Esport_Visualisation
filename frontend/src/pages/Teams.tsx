import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { api, yearOf, type Row } from "../api";
import { useAsync } from "../hooks";
import { useTournaments } from "../store";
import { Loader } from "../components/ui";

interface Col {
  key: string;
  label: string;
  fmt?: (v: any) => string;
  pct?: boolean;   // colour >50 blue / <50 red
  diff?: boolean;  // colour >0 blue / <0 red
}

const COLS: Col[] = [
  { key: "team", label: "Team" },
  { key: "games", label: "G" },
  { key: "record", label: "W-L" },
  { key: "winrate", label: "Win%", pct: true },
  { key: "blue_wr", label: "Blue%", pct: true },
  { key: "red_wr", label: "Red%", pct: true },
  { key: "avg_kills", label: "Avg K" },
  { key: "dragons", label: "🐉" },
  { key: "barons", label: "🟣" },
  { key: "towers", label: "🗼" },
  { key: "GD@15", label: "GD@15", diff: true },
];

export default function Teams() {
  const { selected } = useTournaments();
  const nav = useNavigate();
  const op = selected?.overviewpage ?? "";
  const year = yearOf(selected?.name);
  const { data, error, loading } = useAsync(
    () => api.teamsLeaderboard(op, year ?? undefined),
    [op, year],
  );
  const [sortKey, setSortKey] = useState("winrate");
  const [asc, setAsc] = useState(false);

  if (loading || error) return <Loader error={error} loading={loading} />;
  if (!data || data.length === 0) return <div className="empty">No teams for this tournament.</div>;

  const rows = [...data].sort((a, b) => {
    const av = a[sortKey], bv = b[sortKey];
    if (typeof av === "number" && typeof bv === "number") return asc ? av - bv : bv - av;
    return asc ? String(av).localeCompare(String(bv)) : String(bv).localeCompare(String(av));
  });

  const click = (key: string) => {
    if (key === sortKey) setAsc(!asc);
    else {
      setSortKey(key);
      setAsc(key === "team"); // text asc, numbers desc by default
    }
  };

  const cell = (c: Col, r: Row) => {
    if (c.key === "record") return `${r.wins}-${r.losses}`;
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
      <h2>🏆 Teams</h2>
      <p className="muted">
        All teams in <strong>{selected?.name}</strong> — click a team to open its scouting page.
      </p>
      <div className="table-wrap">
        <table>
          <thead>
            <tr>
              {COLS.map((c) => (
                <th
                  key={c.key}
                  className={`sortable${c.key === "team" ? "" : " num"}${sortKey === c.key ? " sorted" : ""}`}
                  onClick={() => click(c.key)}
                >
                  {c.label}
                  {sortKey === c.key ? (asc ? " ▲" : " ▼") : ""}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.map((r, i) => (
              <tr key={i} className="clickable" onClick={() => nav(`/team?team=${encodeURIComponent(r.team)}`)}>
                {COLS.map((c) => (
                  <td key={c.key} className={c.key === "team" ? "team-cell" : "num"}>
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
