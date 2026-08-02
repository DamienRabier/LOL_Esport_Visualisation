import { useMemo, useState } from "react";
import { api, type Row } from "../api";
import { useAsync } from "../hooks";
import { useTournaments } from "../store";
import { Loader } from "../components/ui";

export default function AddData() {
  const { reload } = useTournaments();
  const [catalogNonce, setCatalogNonce] = useState(0);
  const { data: catalog } = useAsync(() => api.catalog(), [catalogNonce]);

  const [region, setRegion] = useState("All");
  const [year, setYear] = useState("All");
  const [choice, setChoice] = useState("");
  const [manual, setManual] = useState("");
  const [busy, setBusy] = useState(false);
  const [steps, setSteps] = useState<{ label: string; rows: number }[] | null>(null);
  const [msg, setMsg] = useState<{ kind: "ok" | "err"; text: string } | null>(null);

  const rows: Row[] = catalog ?? [];
  const regions = useMemo(
    () => ["All", ...Array.from(new Set(rows.map((r) => r.region).filter(Boolean))).sort()],
    [rows],
  );
  const years = useMemo(
    () =>
      ["All", ...Array.from(new Set(rows.map((r) => String(r.year)).filter((y) => y && y !== "null"))).sort().reverse()],
    [rows],
  );
  const filtered = rows.filter(
    (r) => (region === "All" || r.region === region) && (year === "All" || String(r.year) === year),
  );

  async function refresh(scope: "recent" | "full") {
    setBusy(true);
    setMsg(null);
    try {
      const { count } = await api.refreshCatalog(scope);
      setMsg({ kind: "ok", text: `Catalog built: ${count} tournaments.` });
      setCatalogNonce((n) => n + 1);
    } catch (e: any) {
      setMsg({ kind: "err", text: String(e.message || e) });
    } finally {
      setBusy(false);
    }
  }

  async function ingest(name: string) {
    if (!name) return;
    setBusy(true);
    setMsg(null);
    setSteps([]);
    try {
      const res = await api.ingest(name);
      setSteps(res.steps);
      if (res.ok) {
        setMsg({ kind: "ok", text: `Loaded “${name}”.` });
        reload();
      } else {
        setMsg({ kind: "err", text: res.error || "Ingest failed." });
      }
    } catch (e: any) {
      setMsg({ kind: "err", text: String(e.message || e) });
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="page">
      <h2>➕ Add data</h2>
      <p className="muted">Ingest a tournament from Leaguepedia into the database.</p>

      <section className="card">
        <h3>Tournament list (autocomplete source)</h3>
        <p className="muted">{rows.length} tournaments cached.</p>
        <div className="row">
          <button disabled={busy} className="btn primary" onClick={() => refresh("recent")}>
            ⚡ Load recent
          </button>
          <button disabled={busy} className="btn" onClick={() => refresh("full")}>
            Refresh full history
          </button>
        </div>
        <p className="muted small">
          “Load recent” is fast (one request, last 3 years). Full history is slow and rate-limited.
        </p>
      </section>

      {rows.length > 0 && (
        <section className="card">
          <h3>Pick from the catalog</h3>
          <div className="row">
            <select value={region} onChange={(e) => setRegion(e.target.value)} className="select">
              {regions.map((r) => (
                <option key={r}>{r}</option>
              ))}
            </select>
            <select value={year} onChange={(e) => setYear(e.target.value)} className="select">
              {years.map((y) => (
                <option key={y}>{y}</option>
              ))}
            </select>
          </div>
          <select value={choice} onChange={(e) => setChoice(e.target.value)} className="select full">
            <option value="">{`Select a tournament (${filtered.length} match)…`}</option>
            {filtered.map((r) => (
              <option key={r.overviewpage} value={r.name}>
                {r.name}
              </option>
            ))}
          </select>
          <button disabled={busy || !choice} className="btn primary" onClick={() => ingest(choice)}>
            Fetch & load
          </button>
        </section>
      )}

      <section className="card">
        <h3>Type the name manually</h3>
        <div className="row">
          <input
            value={manual}
            onChange={(e) => setManual(e.target.value)}
            placeholder="e.g. MSI 2026"
            className="input"
          />
          <button disabled={busy || !manual.trim()} className="btn primary" onClick={() => ingest(manual.trim())}>
            Fetch & load
          </button>
        </div>
      </section>

      {busy && <Loader loading />}
      {steps && steps.length > 0 && (
        <ul className="steps">
          {steps.map((s, i) => (
            <li key={i}>
              <strong>{s.label}:</strong> {s.rows} rows
            </li>
          ))}
        </ul>
      )}
      {msg && <div className={msg.kind === "ok" ? "success" : "error"}>{msg.text}</div>}
    </div>
  );
}
