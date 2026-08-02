import { useState } from "react";
import { useSearchParams } from "react-router-dom";
import { api } from "../api";
import { useAsync } from "../hooks";
import { useTournaments } from "../store";
import { DataTable, Loader, Metric } from "../components/ui";

export default function Games() {
  const { selected } = useTournaments();
  const op = selected?.overviewpage ?? "";
  const { data: games, error, loading } = useAsync(() => api.games(op), [op]);
  const [params, setParams] = useSearchParams();
  const [gameid, setGameid] = useState<string>("");

  if (loading || error) return <Loader error={error} loading={loading} />;
  if (!games || games.length === 0) return <div className="empty">No games for this tournament.</div>;

  // Priority: explicit user choice, then ?game= (deep link), then newest game.
  const fromUrl = params.get("game");
  const known = (id: string | null) => (id && games.some((g) => g.gameid === id) ? id : null);
  const current = known(gameid) || known(fromUrl) || games[0].gameid;

  const choose = (id: string) => {
    setGameid(id);
    setParams(id ? { game: id } : {}, { replace: true });
  };

  const label = (r: any) => {
    const d = r.date ? String(r.date).slice(0, 10) : "?";
    const s1 = r.team1score ?? "";
    const s2 = r.team2score ?? "";
    return `${d} — ${r.team1} ${s1}–${s2} ${r.team2}`;
  };

  return (
    <div className="page">
      <h2>🎮 Games</h2>
      <select value={current} onChange={(e) => choose(e.target.value)} className="select">
        {games.map((g) => (
          <option key={g.gameid} value={g.gameid}>
            {label(g)}
          </option>
        ))}
      </select>
      <GameDetail gameid={current} />
    </div>
  );
}

function GameDetail({ gameid }: { gameid: string }) {
  const { data, error, loading } = useAsync(() => api.game(gameid), [gameid]);
  if (loading || error) return <Loader error={error} loading={loading} />;
  if (!data) return null;
  const g = data.detail;
  const winner = g.winner === 1 ? g.team1 : g.winner === 2 ? g.team2 : "—";

  const teamCard = (side: 1 | 2) => {
    const p = side === 1 ? "team1" : "team2";
    const name = g[`${p}`] as string;
    const isWinner = g.winner === side;
    const stats: [string, any][] = [
      ["⚔️ Kills", g[`${p}kills`]],
      ["💰 Gold", fmtGold(g[`${p}gold`])],
      ["🗼 Towers", g[`${p}towers`]],
      ["🐉 Dragons", g[`${p}dragons`]],
      ["🟣 Barons", g[`${p}barons`]],
      ["👁️ Heralds", g[`${p}riftheralds`]],
      ["🐛 Grubs", g[`${p}voidgrubs`]],
    ];
    const bans = g[`${p}bans`] as string[] | undefined;
    return (
      <div className={`team-card${isWinner ? " winner" : ""}`}>
        <div className="team-card-head">
          <h4>{name || `Team ${side}`}</h4>
          {isWinner && <span className="win-badge">WIN</span>}
        </div>
        <div className="stat-grid">
          {stats.map(([k, v]) => (
            <div className="stat-chip" key={k}>
              <span className="k">{k}</span>
              <span className="v">{v ?? "—"}</span>
            </div>
          ))}
        </div>
        {Array.isArray(bans) && bans.length > 0 && (
          <div className="bans-line">
            Bans:{" "}
            {bans.map((b, i) => (
              <span className="chip" key={i}>
                {b}
              </span>
            ))}
          </div>
        )}
      </div>
    );
  };

  const hasEarly = data.players.some((p) => p.gd15 != null);
  const players = data.players.map((p) => ({
    Team: p.team, Role: p.role, Name: p.name, Champion: p.champion,
    K: p.kills, D: p.deaths, A: p.assists, KDA: p.kda, CS: p.cs, Gold: p.gold,
    DMG: p.dmg, Vision: p.vision,
    ...(hasEarly ? { "GD@10": p.gd10, "GD@15": p.gd15, "CSD@10": p.cd10 } : {}),
    Win: p.win,
  }));

  return (
    <>
      <div className="metric-row">
        <Metric label="Winner" value={winner} />
        <Metric label="Length" value={g.gamelength} />
        <Metric label="Patch" value={g.patch} />
      </div>
      <h3>Team stats</h3>
      <div className="grid-2">
        {teamCard(1)}
        {teamCard(2)}
      </div>
      <h3>Player scoreboard</h3>
      <DataTable rows={players} />
      {!hasEarly && (
        <p className="muted small">Early-game diffs (GD@10/@15) unavailable for this game.</p>
      )}
    </>
  );
}

function fmtGold(v: any): string {
  const n = Number(v);
  if (!v || isNaN(n)) return "—";
  return n >= 1000 ? `${(n / 1000).toFixed(1)}k` : String(n);
}
