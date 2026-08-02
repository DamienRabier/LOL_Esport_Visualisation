import { useNavigate } from "react-router-dom";
import { api, yearOf, type Row } from "../api";
import { useAsync } from "../hooks";
import { useTournaments } from "../store";
import RateBar, { BAN_BLUE } from "../components/RateBar";
import { DataTable, Loader, Metric } from "../components/ui";

const MEDALS = ["🥇", "🥈", "🥉"];

function TopList({ title, rows, valueKey, fmt, diff, onPick }: {
  title: string; rows: Row[]; valueKey: string;
  fmt?: (v: any) => string; diff?: boolean; onPick?: (r: Row) => void;
}) {
  return (
    <div className="card">
      <h3>{title}</h3>
      {(!rows || rows.length === 0) ? (
        <div className="empty">Unavailable for this tournament.</div>
      ) : (
        <ol className="toplist">
          {rows.map((r, i) => {
            const v = r[valueKey];
            const cls = diff ? (v > 0 ? "pct-good" : v < 0 ? "pct-bad" : "") : "";
            const shown = fmt ? fmt(v) : String(v);
            return (
              <li key={i} className={onPick ? "clickable" : undefined}
                onClick={onPick ? () => onPick(r) : undefined}>
                <span className="rank">{MEDALS[i] ?? i + 1}</span>
                <span className="who"><strong>{r.player}</strong> <span className="muted">{r.team}</span></span>
                <span className={`val ${cls}`}>{shown}</span>
              </li>
            );
          })}
        </ol>
      )}
    </div>
  );
}

export default function Overview() {
  const { selected } = useTournaments();
  const nav = useNavigate();
  const op = selected?.overviewpage ?? "";
  const year = yearOf(selected?.name);
  const { data, error, loading } = useAsync(() => api.overview(op, year ?? undefined), [op, year]);

  if (loading || error) return <Loader error={error} loading={loading} />;
  if (!data) return null;
  const k = data.kpis;
  const pick = (r: Row) =>
    nav(`/player?player=${encodeURIComponent(r.player)}&team=${encodeURIComponent(r.team)}`);

  return (
    <div className="page">
      <h2>📊 Overview</h2>
      <div className="metric-row">
        <Metric label="Games" value={k.games} />
        <Metric label="Teams" value={k.teams} />
        <Metric label={k.patches === 1 ? "Patch" : "Patches"} value={k.patches === 1 ? k.patch_list : k.patches} />
        <Metric label="Avg length (min)" value={k.avg_len_min} />
      </div>
      <div className="grid-3">
        <TopList title="🏅 Top KDA" rows={data.top_kda} valueKey="kda" onPick={pick} />
        <TopList title="💥 Top DPM" rows={data.top_dpm} valueKey="dpm"
          fmt={(v) => Number(v).toLocaleString()} onPick={pick} />
        <TopList title="⏱️ Top gold diff @ 15" rows={data.top_gd15} valueKey="gd15"
          diff fmt={(v) => (v > 0 ? `+${v}` : String(v))} onPick={pick} />
      </div>
      <div className="grid-2">
        <RateBar
          rows={data.top_picks}
          labelKey="champion"
          totalKey="picks"
          posKey="wins"
          title="Most-picked champions (win/loss)"
        />
        <div>
          <RateBar
            rows={data.top_bans}
            labelKey="champion"
            totalKey="games"
            posKey="bans"
            title="Most-banned champions (ban rate)"
            posName="Banned"
            showNeg={false}
            posColor={BAN_BLUE}
            sortKey="bans"
          />
        </div>
      </div>
      <details>
        <summary>Pick / ban tables</summary>
        <div className="grid-2">
          <DataTable rows={data.top_picks} pctColumns={["winrate_pct"]} />
          <DataTable rows={data.top_bans} pctColumns={["banrate_pct"]} />
        </div>
      </details>
    </div>
  );
}
