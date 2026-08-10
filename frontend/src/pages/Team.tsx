import { useEffect, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { api, yearOf } from "../api";
import { useAsync } from "../hooks";
import { useTournaments } from "../store";
import RateBar, { BAN_BLUE } from "../components/RateBar";
import DiffBar from "../components/DiffBar";
import { DataTable, Loader, Metric } from "../components/ui";

const pct = (w: number, g: number) => (g ? `${Math.round((100 * w) / g)}%` : "—");

export default function Team() {
  const { selected } = useTournaments();
  const op = selected?.overviewpage ?? "";
  const year = yearOf(selected?.name);
  const { data: teams, error, loading } = useAsync(() => api.teams(op), [op]);
  const [params, setParams] = useSearchParams();
  const [team, setTeam] = useState<string>(params.get("team") ?? "");

  useEffect(() => {
    if (!teams || !teams.length) return;
    const wanted = params.get("team");
    if (wanted && teams.includes(wanted)) setTeam(wanted);
    else if (!teams.includes(team)) setTeam(teams[0]);
  }, [teams, params]); // eslint-disable-line react-hooks/exhaustive-deps

  const choose = (t: string) => {
    setTeam(t);
    setParams(t ? { team: t } : {}, { replace: true });
  };

  if (loading || error) return <Loader error={error} loading={loading} />;
  if (!teams || teams.length === 0) return <div className="empty">No teams.</div>;

  return (
    <div className="page">
      <h2>🛡️ Team scouting</h2>
      <select value={team} onChange={(e) => choose(e.target.value)} className="select">
        {teams.map((t) => (
          <option key={t}>{t}</option>
        ))}
      </select>
      {team && <TeamDetail team={team} op={op} year={year} />}
    </div>
  );
}

function TeamDetail({ team, op, year }: { team: string; op: string; year: string | null }) {
  const nav = useNavigate();
  const { data, error, loading } = useAsync(
    () => api.team(team, op, year ?? undefined),
    [team, op, year],
  );
  if (loading || error) return <Loader error={error} loading={loading} />;
  if (!data) return null;
  const { record: r, objectives: o } = data;

  return (
    <>
      <div className="metric-row">
        <Metric label="Record (games)" value={`${r.wins}-${r.games - r.wins}`} sub={pct(r.wins, r.games)} />
        {r.bo_games != null && (
          <Metric
            label="Record (BO)"
            value={`${r.bo_wins}-${r.bo_games - r.bo_wins}`}
            sub={`${r.bo_winrate}%`}
          />
        )}
        <Metric label="Blue side" value={`${r.blue_wins}/${r.blue_games}`} sub={pct(r.blue_wins, r.blue_games)} />
        <Metric label="Red side" value={`${r.red_wins}/${r.red_games}`} sub={pct(r.red_wins, r.red_games)} />
        <Metric label="Avg kills" value={o.kills} />
      </div>
      <h3>Objective control (avg / game)</h3>
      <div className="metric-row">
        <Metric label="🐉 Dragons" value={o.dragons} />
        <Metric label="🟣 Barons" value={o.barons} />
        <Metric label="🗼 Towers" value={o.towers} />
        <Metric label="👁️ Heralds" value={o.heralds} />
        <Metric label="🐛 Grubs" value={o.grubs} />
      </div>
      <div className="grid-2">
        <RateBar
          rows={data.champion_pool}
          labelKey="champion"
          totalKey="games"
          posKey="wins"
          title="Champion pool (win/loss)"
        />
        <RateBar
          rows={data.bans}
          labelKey="champion"
          totalKey="games"
          posKey="bans"
          title="Bans by this team (ban rate)"
          posName="Banned"
          showNeg={false}
          posColor={BAN_BLUE}
          sortKey="bans"
        />
      </div>
      <h3>Recent games</h3>
      <DataTable
        rows={data.games}
        hideColumns={["gameid"]}
        matchColumn="winner"
        matchValue={team}
        onRowClick={(r) => r.gameid && nav(`/games?game=${encodeURIComponent(r.gameid)}`)}
      />

      {year && <TeamEarly team={team} year={year} />}
    </>
  );
}

function TeamEarly({ team, year }: { team: string; year: string }) {
  const { data, error, loading } = useAsync(() => api.oeTeamProfile(team, year), [team, year]);
  if (loading) return null;
  if (error || !data || data.length === 0) return null;

  const sum = (k: string) => data.reduce((a, r) => a + (Number(r[k]) || 0), 0);
  const gd10 = Math.round(sum("gd10"));
  const gd15 = Math.round(sum("gd15"));
  const fmt = (v: number) => (v > 0 ? `+${v}` : `${v}`);

  return (
    <>
      <h3>⏱️ Early game ({year})</h3>
      <div className="metric-row">
        <Metric label="Team gold diff @ 10" value={fmt(gd10)} />
        <Metric label="Team gold diff @ 15" value={fmt(gd15)} />
        <Metric label="Games (OE)" value={data[0]?.games} />
      </div>
      <DiffBar rows={data} labelKey="role" valueKey="gd15" title="Gold diff @ 15 by role" unit=" gold" limit={5} />
    </>
  );
}
