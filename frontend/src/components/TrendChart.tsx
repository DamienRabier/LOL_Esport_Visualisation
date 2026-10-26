import { useState } from "react";
import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { Row } from "../api";

export interface TrendMetric {
  key: string;
  label: string;
  compute?: (r: Row) => number | null;
}

const LINE = "#b4541c";   // accent
const AVG = "#6f7c2f";    // olive

// Line chart of a chosen per-game metric over time, with a 3-game rolling mean.
// `rows` must be oldest -> newest. `labelOf` describes each game for the tooltip.
export default function TrendChart({ title, rows, metrics, labelOf }: {
  title: string; rows: Row[]; metrics: TrendMetric[]; labelOf?: (r: Row) => string;
}) {
  const [mk, setMk] = useState(metrics[0].key);
  const metric = metrics.find((m) => m.key === mk) ?? metrics[0];

  const val = (r: Row): number | null => {
    const v = metric.compute ? metric.compute(r) : Number(r[metric.key]);
    return v == null || Number.isNaN(v) ? null : Math.round(v * 100) / 100;
  };

  const series = rows.map((r, i) => ({
    i: i + 1,
    date: r.date ? String(r.date).slice(0, 10) : "",
    label: labelOf ? labelOf(r) : (r.date ? String(r.date).slice(0, 10) : `Game ${i + 1}`),
    value: val(r),
  }));

  // 3-game rolling average over the available (non-null) points.
  const W = 3;
  const data = series.map((d, idx) => {
    const win = series.slice(Math.max(0, idx - W + 1), idx + 1)
      .map((x) => x.value).filter((v): v is number => v != null);
    const avg = win.length ? Math.round((win.reduce((a, b) => a + b, 0) / win.length) * 100) / 100 : null;
    return { ...d, avg };
  });

  const hasData = data.some((d) => d.value != null);

  return (
    <div className="chart">
      <div className="row" style={{ justifyContent: "space-between", alignItems: "center" }}>
        <h3 style={{ margin: 0 }}>{title}</h3>
        <select className="select" value={mk} onChange={(e) => setMk(e.target.value)}>
          {metrics.map((m) => <option key={m.key} value={m.key}>{m.label}</option>)}
        </select>
      </div>
      {!hasData ? (
        <div className="empty">No data for this metric.</div>
      ) : (
        <ResponsiveContainer width="100%" height={280}>
          <LineChart data={data} margin={{ left: 4, right: 12, top: 12, bottom: 4 }}>
            <CartesianGrid stroke="#e7dac4" vertical={false} />
            <XAxis
              dataKey="i"
              tick={{ fill: "#7a6650", fontSize: 11 }}
              tickLine={false}
              axisLine={{ stroke: "#ddccb6" }}
              interval={Math.max(0, Math.ceil(data.length / 8) - 1)}
              tickFormatter={(i) => data[(i as number) - 1]?.date?.slice(5) ?? ""}
            />
            <YAxis tick={{ fill: "#7a6650", fontSize: 11 }} tickLine={false} axisLine={false} width={48} />
            <Tooltip
              contentStyle={{ background: "#fffaf2", border: "1px solid #ddccb6", borderRadius: 10, color: "#1d1408" }}
              labelFormatter={(i) => data[(i as number) - 1]?.label ?? ""}
              formatter={(v: number, n: string) => [v, n === "avg" ? "3-game avg" : metric.label]}
            />
            <Line type="monotone" dataKey="value" stroke={LINE} strokeWidth={2} dot={{ r: 2.5 }} connectNulls name={metric.label} />
            <Line type="monotone" dataKey="avg" stroke={AVG} strokeWidth={2} strokeDasharray="5 4" dot={false} connectNulls name="avg" />
          </LineChart>
        </ResponsiveContainer>
      )}
    </div>
  );
}
