import { useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { api, type Row } from "../api";
import { useAsync } from "../hooks";
import { useTournaments } from "../store";
import { DataTable, Loader, Metric } from "../components/ui";

export default function Games() {
  const { selected } = useTournaments();
  const op = selected?.overviewpage ?? "";
  const [params, setParams] = useSearchParams();
  const [mode, setMode] = useState<"games" | "bos">("games");

  return (
    <div className="page">
      <div className="page-head">
        <h2>🎮 {mode === "games" ? "Games" : "BOs"}</h2>
        <div className="toggle">
          <button className={mode === "games" ? "on" : ""} onClick={() => setMode("games")}>Games</button>
          <button className={mode === "bos" ? "on" : ""} onClick={() => setMode("bos")}>BOs</button>
        </div>
      </div>
      {mode === "games" ? (
        <GamesView op={op} params={params} setParams={setParams} />
      ) : (
        <BosView op={op} onOpenGame={(id) => { setParams({ game: id }, { replace: true }); setMode("games"); }} />
      )}
    </div>
  );
}

function GamesView({ op, params, setParams }: {
  op: string;
  params: URLSearchParams;
  setParams: (p: Record<string, string>, o?: { replace?: boolean }) => void;
}) {
  const { data: games, error, loading } = useAsync(() => api.games(op), [op]);
  const [gameid, setGameid] = useState<string>("");

  if (loading || error) return <Loader error={error} loading={loading} />;
  if (!games || games.length === 0) return <div className="empty">No games for this tournament.</div>;

  const fromUrl = params.get("game");
  const known = (id: string | null) => (id && games.some((g) => g.gameid === id) ? id : null);
  const current = known(gameid) || known(fromUrl) || games[0].gameid;

  const choose = (id: string) => {
    setGameid(id);
    setParams(id ? { game: id } : {}, { replace: true });
  };

  const label = (r: any) => {
    const d = r.date ? String(r.date).slice(0, 10) : "?";
    return `${d} — ${r.team1} ${r.team1score ?? ""}–${r.team2score ?? ""} ${r.team2}`;
  };

  return (
    <>
      <select value={current} onChange={(e) => choose(e.target.value)} className="select">
        {games.map((g) => (
          <option key={g.gameid} value={g.gameid}>{label(g)}</option>
        ))}
      </select>
      <GameDetail gameid={current} />
    </>
  );
}

function BosView({ op, onOpenGame }: { op: string; onOpenGame: (gameid: string) => void }) {
  const { data: matches, error, loading } = useAsync(() => api.matches(op), [op]);
  const [matchid, setMatchid] = useState<string>("");

  useEffect(() => {
    if (matches && matches.length && !matches.some((m) => m.matchid === matchid))
      setMatchid(matches[0].matchid);
  }, [matches]); // eslint-disable-line react-hooks/exhaustive-deps

  if (loading || error) return <Loader error={error} loading={loading} />;
  if (!matches || matches.length === 0) return <div className="empty">No BOs for this tournament.</div>;

  const label = (m: Row) => {
    const d = m.date ? String(m.date).slice(0, 10) : "?";
    return `${d} — ${m.team1} ${m.t1}–${m.t2} ${m.team2} (Bo${m.bo})`;
  };
  const current = matches.find((m) => m.matchid === matchid) ?? matches[0];

  return (
    <>
      <select value={current.matchid} onChange={(e) => setMatchid(e.target.value)} className="select">
        {matches.map((m) => (
          <option key={m.matchid} value={m.matchid}>{label(m)}</option>
        ))}
      </select>
      <MatchDetail match={current} onOpenGame={onOpenGame} />
    </>
  );
}

function MatchDetail({ match, onOpenGame }: { match: Row; onOpenGame: (gameid: string) => void }) {
  const { data, error, loading } = useAsync(() => api.match(match.matchid), [match.matchid]);
  if (loading || error) return <Loader error={error} loading={loading} />;
  if (!data) return null;

  const gameRows = data.games.map((g) => ({
    gameid: g.gameid,
    Game: g.game, Date: g.date, Team1: g.team1, Team2: g.team2,
    Winner: g.winner, Length: g.length, Patch: g.patch,
  }));
  const players = data.players.map((p) => ({
    Team: p.team, Role: p.role, Name: p.name, Games: p.games,
    "K/D/A": `${p.k}/${p.d}/${p.a}`, KDA: p.kda, "Avg CS": p.cs,
    DMG: Number(p.dmg).toLocaleString(), Vision: p.vision,
  }));

  return (
    <>
      <div className="metric-row">
        <Metric label="Winner" value={match.winner} />
        <Metric label="Score" value={`${match.t1}–${match.t2}`} />
        <Metric label="Format" value={`Bo${match.bo}`} />
        <Metric label="Games" value={match.games} />
      </div>
      <h3>Games in this BO</h3>
      <DataTable
        rows={gameRows}
        hideColumns={["gameid"]}
        matchColumn="Winner"
        matchValue={match.winner}
        onRowClick={(r) => r.gameid && onOpenGame(r.gameid as string)}
      />
      <h3>Series totals (player)</h3>
      <DataTable rows={players} />
    </>
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
