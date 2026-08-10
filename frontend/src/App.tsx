import { NavLink, Route, Routes } from "react-router-dom";
import { useTournaments } from "./store";
import Overview from "./pages/Overview";
import Games from "./pages/Games";
import Team from "./pages/Team";
import Player from "./pages/Player";
import Draft from "./pages/Draft";
import Teams from "./pages/Teams";
import Players from "./pages/Players";
import AddData from "./pages/AddData";
import RefreshStatus from "./components/RefreshStatus";
import RefreshOverlay from "./components/RefreshOverlay";
import ErrorBoundary from "./components/ErrorBoundary";
import OeRefreshButton from "./components/OeRefreshButton";
import TournamentPicker from "./components/TournamentPicker";

const NAV = [
  { to: "/", label: "📊 Overview", end: true },
  { to: "/games", label: "🎮 Games" },
  { to: "/teams", label: "🏆 Teams" },
  { to: "/team", label: "🛡️ Team scouting" },
  { to: "/players", label: "🧑 Players" },
  { to: "/player", label: "🧍 Player scouting" },
  { to: "/draft", label: "🚫 Draft" },
];

export default function App() {
  const { tournaments, loading, error } = useTournaments();

  return (
    <div className="app">
      <RefreshOverlay />
      <aside className="sidebar">
        <div className="brand">🎮 LoL Esport</div>

        <TournamentPicker />

        <nav>
          {NAV.map((n) => (
            <NavLink key={n.to} to={n.to} end={n.end} className="nav-link">
              {n.label}
            </NavLink>
          ))}
        </nav>

        <div className="sidebar-spacer" />
        <RefreshStatus />
        <OeRefreshButton />
        <NavLink to="/add" className="nav-link add">
          ➕ Add data
        </NavLink>
        {error && <div className="error small">{error}</div>}
      </aside>

      <main className="content">
        <ErrorBoundary>
          {tournaments.length === 0 && !loading ? (
            <EmptyState />
          ) : (
            <Routes>
              <Route path="/" element={<Overview />} />
              <Route path="/games" element={<Games />} />
              <Route path="/teams" element={<Teams />} />
              <Route path="/team" element={<Team />} />
              <Route path="/players" element={<Players />} />
              <Route path="/player" element={<Player />} />
              <Route path="/draft" element={<Draft />} />
              <Route path="/add" element={<AddData />} />
            </Routes>
          )}
        </ErrorBoundary>
      </main>
    </div>
  );
}

function EmptyState() {
  return (
    <div className="page">
      <h2>Welcome 👋</h2>
      <p className="muted">
        No data yet. Head to <strong>➕ Add data</strong> to ingest your first tournament, then the
        Overview, Games, Team, Player and Draft views will unlock.
      </p>
      <AddData />
    </div>
  );
}
