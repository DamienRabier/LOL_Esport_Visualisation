import {
  Bar,
  BarChart,
  LabelList,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { Row } from "../api";

const WIN_GREEN = "#6f7c2f";
const LOSS_RED = "#a33327";
const BAN_BLUE = "#b4541c";
const POS_INK = "#f6fbe8"; // text on win/accent segments
const NEG_INK = "#fff0ed"; // text on loss segments
const AXIS_INK = "#1d1408";
const COUNT_INK = "#7a6650";

interface Props {
  rows: Row[];
  labelKey: string; // e.g. "champion"
  totalKey: string; // e.g. "picks" | "games"
  posKey: string; // e.g. "wins" | "bans"
  title: string;
  posName?: string; // legend / tooltip label for the positive segment
  negName?: string;
  showNeg?: boolean;
  posColor?: string;
  sortKey?: string; // defaults to totalKey
  limit?: number;
}

interface Datum {
  label: string;
  pos: number;
  neg: number;
  total: number;
  posRate: number;
  negRate: number;
}

// Horizontal stacked bar mirroring the old Streamlit win/loss & ban-rate charts,
// with gradient fills, rounded ends and value labels for a cleaner look.
export default function RateBar({
  rows,
  labelKey,
  totalKey,
  posKey,
  title,
  posName = "Wins",
  negName = "Losses",
  showNeg = true,
  posColor = WIN_GREEN,
  sortKey,
  limit = 15,
}: Props) {
  const gid = `grad-${posKey}-${posColor.replace("#", "")}`;
  const gidNeg = "grad-neg";

  const data: Datum[] = rows
    .map((r) => {
      const total = Number(r[totalKey]) || 0;
      const pos = Number(r[posKey]) || 0;
      const neg = Math.max(total - pos, 0);
      return {
        label: r[labelKey],
        pos,
        neg,
        total,
        posRate: total ? Math.round((100 * pos) / total) : 0,
        negRate: total ? Math.round((100 * neg) / total) : 0,
      };
    })
    .sort((a, b) => {
      const byPos = (sortKey || totalKey) === posKey;
      return (byPos ? b.pos : b.total) - (byPos ? a.pos : a.total);
    })
    .slice(0, limit); // largest first -> rendered at the top (descending)

  if (data.length === 0) return <div className="empty">No data.</div>;

  return (
    <div className="chart">
      <h3>{title}</h3>
      <ResponsiveContainer width="100%" height={Math.max(280, 34 * data.length + 20)}>
        <BarChart
          data={data}
          layout="vertical"
          margin={{ left: 4, right: 40, top: 4, bottom: 4 }}
          barCategoryGap="28%"
        >
          <defs>
            <linearGradient id={gid} x1="0" y1="0" x2="1" y2="0">
              <stop offset="0%" stopColor={posColor} stopOpacity={0.75} />
              <stop offset="100%" stopColor={posColor} stopOpacity={1} />
            </linearGradient>
            <linearGradient id={gidNeg} x1="0" y1="0" x2="1" y2="0">
              <stop offset="0%" stopColor={LOSS_RED} stopOpacity={0.7} />
              <stop offset="100%" stopColor={LOSS_RED} stopOpacity={0.95} />
            </linearGradient>
          </defs>

          <XAxis type="number" hide />
          <YAxis
            type="category"
            dataKey="label"
            width={116}
            axisLine={false}
            tickLine={false}
            tick={{ fill: AXIS_INK, fontSize: 13, fontWeight: 500 }}
          />
          <Tooltip cursor={{ fill: "rgba(148,163,184,0.08)" }} content={<ChartTooltip posName={posName} negName={negName} />} />

          <Bar
            dataKey="pos"
            stackId="s"
            name={posName}
            fill={`url(#${gid})`}
            radius={showNeg ? [4, 0, 0, 4] : [4, 4, 4, 4]}
            isAnimationActive
            animationDuration={550}
          >
            <LabelList
              dataKey="posRate"
              position="center"
              formatter={(v: number) => (v >= 12 ? `${v}%` : "")}
              fill={POS_INK}
              fontSize={11}
              fontWeight={700}
            />
            {!showNeg && (
              <LabelList
                dataKey="pos"
                position="right"
                fill={COUNT_INK}
                fontSize={11}
                offset={8}
              />
            )}
          </Bar>

          {showNeg && (
            <Bar
              dataKey="neg"
              stackId="s"
              name={negName}
              fill={`url(#${gidNeg})`}
              radius={[0, 4, 4, 0]}
              isAnimationActive
              animationDuration={550}
            >
              <LabelList
                dataKey="negRate"
                position="center"
                formatter={(v: number) => (v >= 12 ? `${v}%` : "")}
                fill={NEG_INK}
                fontSize={11}
                fontWeight={700}
              />
              <LabelList
                dataKey="total"
                position="right"
                fill={COUNT_INK}
                fontSize={11}
                offset={8}
              />
            </Bar>
          )}
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}

function ChartTooltip({
  active,
  payload,
  posName,
  negName,
}: any) {
  if (!active || !payload || !payload.length) return null;
  const d: Datum = payload[0].payload;
  return (
    <div className="tooltip-card">
      <div className="tooltip-title">{d.label}</div>
      <div className="tooltip-row">
        <span className="dot" style={{ background: payload[0].color }} />
        {posName}: <strong>{d.pos}</strong> ({d.posRate}%)
      </div>
      {payload.length > 1 && (
        <div className="tooltip-row">
          <span className="dot" style={{ background: payload[1].color }} />
          {negName}: <strong>{d.neg}</strong> ({d.negRate}%)
        </div>
      )}
      <div className="tooltip-total">total {d.total}</div>
    </div>
  );
}

export { WIN_GREEN, LOSS_RED, BAN_BLUE };
