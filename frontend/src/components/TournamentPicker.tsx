import { useEffect, useMemo, useState } from "react";
import { useTournaments } from "../store";
import type { Tournament } from "../api";

// Tournament names look like "LEC 2026 Summer", "LCK 2026 Rounds 3-4",
// "MSI 2026", "Esports World Cup 2026". Split into league / year / split.
function parse(name: string): { league: string; year: string; split: string } {
  const m = name.match(/^(.*?)\s*(20\d{2})\s*(.*)$/);
  if (!m) return { league: name, year: "", split: "Main" };
  return { league: m[1].trim() || name, year: m[2], split: m[3].trim() || "Main" };
}

interface Parsed extends Tournament {
  league: string;
  year: string;
  split: string;
}

export default function TournamentPicker() {
  const { tournaments, selected, setSelected, loading } = useTournaments();

  const parsed = useMemo<Parsed[]>(
    () => tournaments.map((t) => ({ ...t, ...parse(t.name) })),
    [tournaments],
  );

  const leagues = useMemo(
    () => Array.from(new Set(parsed.map((p) => p.league))).sort((a, b) => a.localeCompare(b)),
    [parsed],
  );

  const [league, setLeague] = useState("");
  const [year, setYear] = useState("");

  // Keep the cascade in sync with the externally-selected tournament
  // (initial default, or after a data refresh).
  useEffect(() => {
    if (!selected) return;
    const p = parse(selected.name);
    setLeague(p.league);
    setYear(p.year);
  }, [selected]);

  const years = useMemo(
    () =>
      Array.from(new Set(parsed.filter((p) => p.league === league).map((p) => p.year)))
        .sort((a, b) => b.localeCompare(a)),
    [parsed, league],
  );

  const splits = useMemo(
    () => parsed.filter((p) => p.league === league && p.year === year),
    [parsed, league, year],
  );

  const pickFirst = (l: string, y: string) => {
    const t = parsed.find((p) => p.league === l && p.year === y);
    if (t) setSelected(t);
  };

  const onLeague = (l: string) => {
    setLeague(l);
    const ys = Array.from(new Set(parsed.filter((p) => p.league === l).map((p) => p.year))).sort(
      (a, b) => b.localeCompare(a),
    );
    const y = ys[0] ?? "";
    setYear(y);
    pickFirst(l, y);
  };

  const onYear = (y: string) => {
    setYear(y);
    pickFirst(league, y);
  };

  const ALL = "__ALL__";
  const isAll = (selected?.overviewpage ?? "").includes("\n");

  const onSplit = (op: string) => {
    if (op === ALL) {
      setSelected({
        name: `${league} ${year} — All splits`,
        overviewpage: splits.map((s) => s.overviewpage).join("\n"),
      });
      return;
    }
    const t = parsed.find((p) => p.overviewpage === op);
    if (t) setSelected(t);
  };

  if (!tournaments.length) {
    return (
      <div className="picker">
        <span className="field-label">Tournament</span>
        <select className="select full" disabled>
          <option>{loading ? "Loading…" : "No data yet"}</option>
        </select>
      </div>
    );
  }

  return (
    <div className="picker">
      <label className="field-label">League</label>
      <select className="select full" value={league} onChange={(e) => onLeague(e.target.value)}>
        {leagues.map((l) => (
          <option key={l} value={l}>{l}</option>
        ))}
      </select>

      <label className="field-label">Year</label>
      <select className="select full" value={year} onChange={(e) => onYear(e.target.value)}>
        {years.map((y) => (
          <option key={y} value={y}>{y}</option>
        ))}
      </select>

      <label className="field-label">Split</label>
      <select
        className="select full"
        value={isAll ? ALL : (selected?.overviewpage ?? "")}
        onChange={(e) => onSplit(e.target.value)}
      >
        {splits.length > 1 && <option value={ALL}>★ All splits</option>}
        {splits.map((s) => (
          <option key={s.overviewpage} value={s.overviewpage}>{s.split}</option>
        ))}
      </select>
    </div>
  );
}
