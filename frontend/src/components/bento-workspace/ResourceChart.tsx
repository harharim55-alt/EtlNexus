import {
  LineChart,
  Line,
  AreaChart,
  Area,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
  ReferenceLine,
} from "recharts";

/* ── Chart theme (shared with parent) ────────────────────────────── */

const GRID_COLOR = "var(--border)";
const TICK_STYLE = { fill: "var(--text-muted)", fontSize: 9, fontFamily: "monospace" };
const TOOLTIP_STYLE = {
  contentStyle: {
    backgroundColor: "var(--surface-modal)",
    border: "1px solid var(--border)",
    borderRadius: 8,
    fontSize: 11,
    fontFamily: "monospace",
    color: "var(--text-primary)",
  },
  labelStyle: { color: "var(--text-muted)", fontSize: 10 },
};

/* ── Types ────────────────────────────────────────────────────────── */

interface ChartLine {
  dataKey: string;
  stroke: string;
  name: string;
  strokeWidth?: number;
  strokeDasharray?: string;
  /** Custom dot component (for LineChart only) */
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  dot?: any;
}

interface ChartBar {
  dataKey: string;
  fill: string;
  fillOpacity?: number;
  name: string;
}

interface ChartArea {
  dataKey: string;
  stroke: string;
  strokeWidth?: number;
  fill: string;
  name: string;
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  dot?: any;
}

interface ChartReferenceLine {
  y: number;
  stroke: string;
  strokeDasharray?: string;
  label?: string;
  labelFormatter?: (value: number) => string;
}

interface ResourceChartProps {
  title: string;
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  data: any[];
  chartType: "line" | "area" | "bar";
  lines?: ChartLine[];
  bars?: ChartBar[];
  areas?: ChartArea[];
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  yTickFormatter?: (value: number) => string;
  yDomain?: [number, number];
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  tooltipFormatter?: (value: any, name: any, props?: any) => [string, string];
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  labelFormatter?: (label: any, payload: readonly any[]) => string;
  showLegend?: boolean;
  /** Recharts gradient defs (for area charts) */
  gradientDefs?: React.ReactNode;
  /** Horizontal reference lines (e.g. p90 thresholds) */
  referenceLines?: ChartReferenceLine[];
  /** Click handler for the chart (receives Recharts click event data) */
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  onChartClick?: (data: any) => void;
}

/* ── Panel wrapper ────────────────────────────────────────────────── */

function ChartPanel({
  title,
  children,
}: {
  title: string;
  children: React.ReactNode;
}) {
  return (
    <div className="bg-hover-bg border border-border rounded-xl p-4">
      <div className="text-[9px] font-mono uppercase tracking-widest text-text-faint mb-3">
        {title}
      </div>
      <div className="h-[200px]">{children}</div>
    </div>
  );
}

/* ── ResourceChart ────────────────────────────────────────────────── */

export function ResourceChart({
  title,
  data,
  chartType,
  lines,
  bars,
  areas,
  yTickFormatter,
  yDomain,
  tooltipFormatter,
  labelFormatter,
  showLegend = false,
  gradientDefs,
  referenceLines,
  onChartClick,
}: ResourceChartProps) {
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const defaultLabelFormatter = (_: any, payload: any) =>
    payload?.[0]?.payload?.dateFull ?? "";

  const resolvedLabelFormatter = labelFormatter ?? defaultLabelFormatter;

  return (
    <ChartPanel title={title}>
      <ResponsiveContainer width="100%" height="100%">
        {chartType === "bar" ? (
          <BarChart data={data} onClick={onChartClick}>
            <CartesianGrid strokeDasharray="3 3" stroke={GRID_COLOR} />
            <XAxis dataKey="date" tick={TICK_STYLE} axisLine={false} tickLine={false} />
            <YAxis
              tick={TICK_STYLE}
              axisLine={false}
              tickLine={false}
              tickFormatter={yTickFormatter}
              domain={yDomain}
            />
            <Tooltip
              {...TOOLTIP_STYLE}
              formatter={tooltipFormatter}
              labelFormatter={resolvedLabelFormatter}
            />
            {showLegend && (
              <Legend
                iconSize={8}
                wrapperStyle={{ fontSize: 9, fontFamily: "monospace" }}
              />
            )}
            {referenceLines?.map((ref, i) => (
              <ReferenceLine
                key={`ref-${i}`}
                y={ref.y}
                stroke={ref.stroke}
                strokeDasharray={ref.strokeDasharray ?? "6 3"}
                label={{
                  value: ref.labelFormatter ? ref.labelFormatter(ref.y) : (ref.label ?? ""),
                  position: "right",
                  fill: ref.stroke,
                  fontSize: 9,
                  fontFamily: "monospace",
                }}
              />
            ))}
            {bars?.map((bar) => (
              <Bar
                key={bar.dataKey}
                dataKey={bar.dataKey}
                fill={bar.fill}
                fillOpacity={bar.fillOpacity ?? 0.7}
                name={bar.name}
                radius={[2, 2, 0, 0]}
              />
            ))}
          </BarChart>
        ) : chartType === "area" ? (
          <AreaChart data={data} onClick={onChartClick}>
            {gradientDefs && <defs>{gradientDefs}</defs>}
            <CartesianGrid strokeDasharray="3 3" stroke={GRID_COLOR} />
            <XAxis dataKey="date" tick={TICK_STYLE} axisLine={false} tickLine={false} />
            <YAxis
              tick={TICK_STYLE}
              axisLine={false}
              tickLine={false}
              tickFormatter={yTickFormatter}
              domain={yDomain}
            />
            <Tooltip
              {...TOOLTIP_STYLE}
              formatter={tooltipFormatter}
              labelFormatter={resolvedLabelFormatter}
            />
            {showLegend && (
              <Legend
                iconSize={8}
                wrapperStyle={{ fontSize: 9, fontFamily: "monospace" }}
              />
            )}
            {referenceLines?.map((ref, i) => (
              <ReferenceLine
                key={`ref-${i}`}
                y={ref.y}
                stroke={ref.stroke}
                strokeDasharray={ref.strokeDasharray ?? "6 3"}
                label={{
                  value: ref.labelFormatter ? ref.labelFormatter(ref.y) : (ref.label ?? ""),
                  position: "right",
                  fill: ref.stroke,
                  fontSize: 9,
                  fontFamily: "monospace",
                }}
              />
            ))}
            {areas?.map((area) => (
              <Area
                key={area.dataKey}
                type="monotone"
                dataKey={area.dataKey}
                stroke={area.stroke}
                strokeWidth={area.strokeWidth ?? 1.5}
                fill={area.fill}
                dot={area.dot ?? { r: 2, fill: area.stroke }}
                name={area.name}
              />
            ))}
          </AreaChart>
        ) : (
          <LineChart data={data} onClick={onChartClick}>
            <CartesianGrid strokeDasharray="3 3" stroke={GRID_COLOR} />
            <XAxis dataKey="date" tick={TICK_STYLE} axisLine={false} tickLine={false} />
            <YAxis
              tick={TICK_STYLE}
              axisLine={false}
              tickLine={false}
              tickFormatter={yTickFormatter}
              domain={yDomain}
            />
            <Tooltip
              {...TOOLTIP_STYLE}
              formatter={tooltipFormatter}
              labelFormatter={resolvedLabelFormatter}
            />
            {showLegend && (
              <Legend
                iconSize={8}
                wrapperStyle={{ fontSize: 9, fontFamily: "monospace" }}
              />
            )}
            {referenceLines?.map((ref, i) => (
              <ReferenceLine
                key={`ref-${i}`}
                y={ref.y}
                stroke={ref.stroke}
                strokeDasharray={ref.strokeDasharray ?? "6 3"}
                label={{
                  value: ref.labelFormatter ? ref.labelFormatter(ref.y) : (ref.label ?? ""),
                  position: "right",
                  fill: ref.stroke,
                  fontSize: 9,
                  fontFamily: "monospace",
                }}
              />
            ))}
            {lines?.map((line) => (
              <Line
                key={line.dataKey}
                type="monotone"
                dataKey={line.dataKey}
                stroke={line.stroke}
                strokeWidth={line.strokeWidth ?? 1.5}
                strokeDasharray={line.strokeDasharray}
                dot={line.dot ?? { r: 2, fill: line.stroke }}
                name={line.name}
              />
            ))}
          </LineChart>
        )}
      </ResponsiveContainer>
    </ChartPanel>
  );
}
