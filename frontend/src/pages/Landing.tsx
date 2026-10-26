const FEATURES = [
  { icon: "📊", title: "Scout at a glance", text: "Win rates, pick/ban trends and draft priorities for every tracked league." },
  { icon: "🛡️", title: "Teams & players", text: "Leaderboards plus deep per-team and per-player scouting pages." },
  { icon: "📈", title: "Per-game trends", text: "Track how a team or player evolves game by game, with early-game diffs." },
];

export default function Landing({ onEnter }: { onEnter: () => void }) {
  return (
    <div className="landing">
      <div className="landing-inner">
        <div className="landing-badge">LoL Esport Analytics</div>
        <h1 className="landing-title">
          Debrief & scout the
          <br />
          <span className="landing-accent">competitive rift</span>
        </h1>
        <p className="landing-tagline">
          A scouting cockpit over Leaguepedia &amp; Oracle&apos;s Elixir — picks, bans, drafts,
          team &amp; player form, all kept up to date automatically.
        </p>

        <div className="landing-cta">
          <button className="btn primary landing-enter" onClick={onEnter}>
            Enter dashboard →
          </button>
        </div>

        <div className="landing-features">
          {FEATURES.map((f) => (
            <div key={f.title} className="landing-feature">
              <span className="lf-icon">{f.icon}</span>
              <div>
                <div className="lf-title">{f.title}</div>
                <div className="lf-text">{f.text}</div>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
