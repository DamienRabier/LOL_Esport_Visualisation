import { useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { api, yearOf } from "../api";
import { useAsync } from "../hooks";
import { useTournaments } from "../store";
import RateBar from "../components/RateBar";
import { DataTable, Loader, Metric } from "../components/ui";

export default function Player() {
  const { selected } = useTournaments();
  const op = selected?.overviewpage ?? "";
  const year = yearOf(selected?.name);
  const [params, setParams] = useSearchParams();
  const [team, setTeam] = useState<string>(params.get("team") ?? "");
  const [player, setPlayer] = useState<string>(params.get("player") ?? "");

  const { data: teams } = useAsync(() => api.teams(op), [op]);
  const { data: players, error, loading } = useAsync(
    () => api.players(op, team || undefined),
    [op, team],
  );

  useEffect(() => {
    if (!players || !players.length) return;
    const wanted = params.get("player");
    if (wanted && players.includes(wanted)) setPlayer(wanted);
    else if (!players.includes(player)) setPlayer(players[0]);
  }, [players, params]); // eslint-disable-line react-hooks/exhaustive-deps

  const chooseTeam = (t: string) => { setTeam(t); setParams({}, { replace: true }); };
  const choosePlayer = (p: string) => {
    setPlayer(p);
    setParams(p ? { player: p, ...(team ? { team } : {}) } : {}, { replace: true });
  };

  return (
    <div className="page">
      <h2>🧍 Player scouting</h2>
      <div className="row">
        <select value={team} onChange={(e) => chooseTeam(e.target.value)} className="select">
          <option value="">All teams</option>
          {(teams ?? []).map((t) => (
            <option key={t}>{t}</option>
          ))}
        </select>
        <select value={player} onChange={(e) => choosePlayer(e.target.value)} className="select">
          {(players ?? []).map((p) => (
            <option key={p}>{p}</option>
          ))}
        </select>
      </div>
      <Loader error={error} loading={loading} />
      {player && op && <PlayerDetail player={player} op={op} year={year} />}
    </div>
  );
}

function PlayerDetail({ player, op, year }: { player: string; op: string; year: string | null }) {
  const { data, error, loading } = useAsync(
    () => api.player(player, op, year ?? undefined),
    [player, op, year],
  );
  if (loading || error) return <Loader error={error} loading={loading} />;
  if (!data) return null;
  const s = data.summary;

  return (
    <>
      <div className="metric-row">
        <Metric label="Games" value={s.games} />
        <Metric label="KDA" value={s.kda} sub={`${s.k}/${s.d}/${s.a}`} />
        <Metric label="Win rate" value={`${s.winrate_pct}%`} />
        <Metric label="Avg CS" value={s.cs} />
        <Metric label="Avg damage" value={s.dmg?.toLocaleString?.()} />
      </div>
      <div className="grid-2">
        <RateBar
          rows={data.champions}
          labelKey="champion"
          totalKey="games"
          posKey="wins"
          title="Champion pool (win/loss)"
        />
        <div>
          <h3>Game log</h3>
          <DataTable rows={data.games} />
        </div>
      </div>
      {year && <PlayerEarly player={player} year={year} />}
    </>
  );
}

function PlayerEarly({ player, year }: { player: string; year: string }) {
  const { data, loading, error } = useAsync(() => api.oePlayerProfile(player, year), [player, year]);
  if (loading || error || !data || !data.games) return null;
  const fmt = (v: any) => (v > 0 ? `+${v}` : `${v}`);
  return (
    <>
      <h3>⏱️ Early game ({year})</h3>
      <div className="metric-row">
        <Metric label="Gold diff @ 10" value={fmt(data.gd10)} />
        <Metric label="Gold diff @ 15" value={fmt(data.gd15)} />
        <Metric label="CS diff @ 10" value={fmt(data.cd10)} />
        <Metric label="XP diff @ 10" value={fmt(data.xd10)} />
        <Metric label="Games (OE)" value={data.games} />
      </div>
    </>
  );
}
