import {
  Bar,
  BarChart,
  Cell,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { Row } from "../api";

const POS = "#6f7c2f";
const NEG = "#a33327";

interface Props {
  rows: Row[];
  labelKey: string;
  valueKey: string;
  title: string;
  unit?: string; // e.g. " gold"
  limit?: number;
  subKey?: string; // optional secondary label (e.g. team) for the tooltip
}

// Diverging horizontal bars centered at zero: green = ahead, red = behind.
// Used for lane-diff metrics (gold/xp/cs diff at 10/15).
export default function DiffBar({ rows, labelKey, valueKey, title, unit = "", limit = 15, subKey }: Props) {
  const data = rows
    .map((r) => ({ ...r, _v: Number(r[valueKey]) || 0 }))
    .sort((a, b) => b._v - a._v)
    .slice(0, limit)
    .reverse();

  if (data.length === 0) return <div className="empty">No data.</div>;

  const m = Math.max(1, ...data.map((d) => Math.abs(d._v)));

  return (
    <div className="chart">
      <h3>{title}</h3>
      <ResponsiveContainer width="100%" height={Math.max(260, 30 * data.length + 20)}>
        <BarChart data={data} layout="vertical" margin={{ left: 6, right: 44, top: 4, bottom: 4 }}>
          <XAxis type="number" domain={[-m * 1.15, m * 1.15]} hide />
          <YAxis
            type="category"
            dataKey={labelKey}
            width={116}
            axisLine={false}
            tickLine={false}
            tick={{ fill: "#1d1408", fontSize: 13, fontWeight: 500 }}
          />
          <ReferenceLine x={0} stroke="#ddccb6" />
          <Tooltip
            cursor={{ fill: "rgba(180,84,28,0.08)" }}
            content={({ active, payload }: any) => {
              if (!active || !payload?.length) return null;
              const d = payload[0].payload;
              return (
                <div className="tooltip-card">
                  <div className="tooltip-title">
                    {d[labelKey]}
                    {subKey && d[subKey] ? <span className="muted"> · {d[subKey]}</span> : null}
                  </div>
                  <div className="tooltip-row">
                    {title}: <strong>{d._v > 0 ? `+${d._v}` : d._v}</strong>
                    {unit}
                  </div>
                </div>
              );
            }}
          />
          <Bar dataKey="_v" radius={3} label={<DiffLabel />}>
            {data.map((d, i) => (
              <Cell key={i} fill={d._v >= 0 ? POS : NEG} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}

function DiffLabel(props: any) {
  const { x, y, width, height, value } = props;
  if (value == null) return null;
  const positive = value >= 0;
  const tx = positive ? x + width + 6 : x - 6;
  return (
    <text
      x={tx}
      y={y + height / 2}
      dy={4}
      textAnchor={positive ? "start" : "end"}
      fontSize={11}
      fontWeight={600}
      fill="#7a6650"
    >
      {positive ? `+${value}` : value}
    </text>
  );
}
