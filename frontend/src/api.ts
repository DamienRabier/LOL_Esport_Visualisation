// Thin typed fetch layer over the FastAPI backend. All paths are same-origin
// (/api/...) — Vite proxies them to :8000 in dev.

export interface Tournament {
  name: string;
  overviewpage: string;
  last_game?: string | null;
}

export type Row = Record<string, any>;

async function getJSON<T>(url: string): Promise<T> {
  const res = await fetch(url);
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.detail || body.error || `HTTP ${res.status}`);
  }
  return res.json();
}

async function postJSON<T>(url: string): Promise<T> {
  const res = await fetch(url, { method: "POST" });
  const body = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(body.detail || body.error || `HTTP ${res.status}`);
  return body as T;
}

const enc = encodeURIComponent;

export const api = {
  tournaments: () => getJSON<Tournament[]>("/api/tournaments"),

  overview: (op: string, year?: string) =>
    getJSON<{ kpis: Row; top_picks: Row[]; top_bans: Row[]; top_kda: Row[]; top_dpm: Row[]; top_gd15: Row[] }>(
      `/api/overview?op=${enc(op)}${year ? `&year=${enc(year)}` : ""}`,
    ),

  games: (op: string) => getJSON<Row[]>(`/api/games?op=${enc(op)}`),
  game: (gameid: string) =>
    getJSON<{ detail: Row; players: Row[] }>(`/api/game?gameid=${enc(gameid)}`),

  teams: (op: string) => getJSON<string[]>(`/api/teams?op=${enc(op)}`),
  teamsLeaderboard: (op: string, year?: string) =>
    getJSON<Row[]>(`/api/teams-leaderboard?op=${enc(op)}${year ? `&year=${enc(year)}` : ""}`),
  team: (name: string, op: string, year?: string) =>
    getJSON<{
      record: Row;
      objectives: Row;
      champion_pool: Row[];
      bans: Row[];
      games: Row[];
    }>(`/api/team?name=${enc(name)}&op=${enc(op)}${year ? `&year=${enc(year)}` : ""}`),

  players: (op: string, team?: string) =>
    getJSON<string[]>(`/api/players?op=${enc(op)}${team ? `&team=${enc(team)}` : ""}`),
  playersLeaderboard: (op: string) => getJSON<Row[]>(`/api/players-leaderboard?op=${enc(op)}`),
  player: (name: string, op: string, year?: string) =>
    getJSON<{ summary: Row; champions: Row[]; games: Row[] }>(
      `/api/player?name=${enc(name)}&op=${enc(op)}${year ? `&year=${enc(year)}` : ""}`,
    ),

  draft: (op: string, year?: string) =>
    getJSON<{ picks: Row[]; bans: Row[] }>(
      `/api/draft?op=${enc(op)}${year ? `&year=${enc(year)}` : ""}`,
    ),

  catalog: () => getJSON<Row[]>("/api/catalog"),
  refreshCatalog: (scope: "recent" | "full") =>
    postJSON<{ count: number }>(`/api/catalog/refresh?scope=${scope}`),
  ingest: (name: string) =>
    postJSON<{ ok: boolean; steps: { label: string; rows: number }[]; error?: string }>(
      `/api/ingest?name=${enc(name)}`,
    ),

  refreshStatus: () => getJSON<RefreshStatus>("/api/refresh/status"),
  startRefresh: () => postJSON<{ started: boolean; running: boolean }>("/api/refresh"),

  // Early game (Oracle's Elixir)
  oeRefresh: () => postJSON<{ started: boolean; running: boolean }>("/api/oe/refresh"),
  oeRefreshStatus: () =>
    getJSON<{ running: boolean; finished_at: string | null; result: OeResult | null }>(
      "/api/oe/refresh/status",
    ),
  oeTeamProfile: (team: string, year: string) =>
    getJSON<Row[]>(`/api/oe/team-profile?team=${enc(team)}&year=${enc(year)}`),
  oePlayerProfile: (player: string, year: string) =>
    getJSON<Row>(`/api/oe/player-profile?player=${enc(player)}&year=${enc(year)}`),
};

export interface OeResult {
  year: number;
  downloaded: boolean;
  reloaded: boolean;
  rows: number;
  error: string | null;
}

// Pull a 4-digit year out of a tournament name (e.g. "MSI 2026" -> "2026").
export function yearOf(name?: string | null): string | null {
  const m = name?.match(/(20\d{2})/);
  return m ? m[1] : null;
}

export interface RefreshStatus {
  running: boolean;
  started_at: string | null;
  finished_at: string | null;
  phase: string | null;
  total: number;
  skipped: number;
  current: { name: string; index: number; total: number } | null;
  done: { name: string; counts: Record<string, number> }[];
  errors: string[];
  oe: { year: number; downloaded: boolean; reloaded: boolean; rows: number; error: string | null } | null;
}
