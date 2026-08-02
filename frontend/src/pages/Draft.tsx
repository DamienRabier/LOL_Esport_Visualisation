import { api, yearOf } from "../api";
import { useAsync } from "../hooks";
import { useTournaments } from "../store";
import { DataTable, Loader } from "../components/ui";

export default function Draft() {
  const { selected } = useTournaments();
  const op = selected?.overviewpage ?? "";
  const year = yearOf(selected?.name);
  const { data, error, loading } = useAsync(() => api.draft(op, year ?? undefined), [op, year]);
  if (loading || error) return <Loader error={error} loading={loading} />;
  if (!data) return null;

  return (
    <div className="page">
      <h2>🚫 Draft</h2>
      <div className="grid-2">
        <div>
          <h3>Picks</h3>
          <DataTable rows={data.picks} />
        </div>
        <div>
          <h3>Bans</h3>
          <DataTable rows={data.bans} />
        </div>
      </div>
    </div>
  );
}
