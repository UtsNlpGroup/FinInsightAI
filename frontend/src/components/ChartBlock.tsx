/**
 * ChartBlock – renders a chart spec embedded by the agent inside a ```chart block.
 *
 * Supported chart types:
 *   • "bar"     – categorical comparisons (vertical bars)
 *   • "bar_h"   – horizontal bar (better for long category labels)
 *   • "line"    – time-series line chart
 *   • "area"    – time-series with filled area
 *   • "pie"     – proportional breakdown
 *   • "donut"   – pie with centre hole + total label
 *   • "scatter" – two-dimensional scatter plot (xKey vs yKeys[0])
 */

import {
  ResponsiveContainer,
  BarChart, Bar,
  LineChart, Line,
  AreaChart, Area,
  ScatterChart, Scatter,
  PieChart, Pie, Cell,
  XAxis, YAxis,
  CartesianGrid, Tooltip, Legend,
  ReferenceLine,
  LabelList,
} from 'recharts';

// ── Types ─────────────────────────────────────────────────────────────────────

export interface YKeySpec {
  key: string;
  label: string;
  color?: string;
}

export interface ChartSpec {
  type: 'bar' | 'bar_h' | 'line' | 'area' | 'pie' | 'donut' | 'scatter';
  title: string;
  subtitle?: string;
  /** Unit applied to numeric values: "$B" | "$M" | "$" | "%" | string */
  unit?: string;
  xKey: string;
  yKeys: YKeySpec[];
  data: Record<string, string | number>[];
  /** Height override in px (default 240, or 300 for pie/donut) */
  height?: number;
}

// ── Palette ───────────────────────────────────────────────────────────────────

const DEFAULT_COLORS = [
  '#7C3AED', '#10B981', '#F59E0B', '#EF4444',
  '#06B6D4', '#8B5CF6', '#EC4899', '#84CC16',
  '#F97316', '#14B8A6', '#6366F1', '#A855F7',
];

function resolveColor(spec: YKeySpec, idx: number): string {
  return spec.color ?? DEFAULT_COLORS[idx % DEFAULT_COLORS.length];
}

function rowColor(row: Record<string, string | number>, idx: number): string {
  return typeof row.color === 'string'
    ? row.color
    : DEFAULT_COLORS[idx % DEFAULT_COLORS.length];
}

// ── Formatters ────────────────────────────────────────────────────────────────

function formatValue(value: number | string, unit?: string): string {
  if (typeof value !== 'number') return String(value);
  if (unit === '$B')  return `$${value.toFixed(1)}B`;
  if (unit === '$M')  return `$${value.toFixed(0)}M`;
  if (unit === '%')   return `${value.toFixed(2)}%`;
  if (unit === '$')   return `$${value.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
  return value.toLocaleString();
}

function tickFormatter(value: number | string, unit?: string): string {
  if (typeof value !== 'number') return String(value);
  if (unit === '$B') return `$${value}B`;
  if (unit === '$M') return `$${value}M`;
  if (unit === '%')  return `${value}%`;
  if (unit === '$')  return `$${value}`;
  return String(value);
}

// ── Custom tooltips ───────────────────────────────────────────────────────────

const tooltipWrapStyle: React.CSSProperties = {
  background: 'rgba(12,14,26,0.92)',
  backdropFilter: 'blur(8px)',
  border: '1px solid rgba(255,255,255,0.1)',
  boxShadow: '0 4px 24px rgba(0,0,0,0.25)',
  borderRadius: 12,
  padding: '10px 14px',
  fontSize: 13,
};

function CartesianTooltip({
  active, payload, label, unit, yKeys,
}: {
  active?: boolean;
  payload?: { value: number; dataKey: string; color: string }[];
  label?: string;
  unit?: string;
  yKeys: YKeySpec[];
}) {
  if (!active || !payload?.length) return null;
  const labelMap = Object.fromEntries(yKeys.map(y => [y.key, y.label]));
  return (
    <div style={tooltipWrapStyle}>
      <p className="font-semibold mb-1.5 text-white">{label}</p>
      {payload.map(entry => (
        <div key={entry.dataKey} className="flex items-center gap-2">
          <span className="inline-block w-2 h-2 rounded-full shrink-0" style={{ background: entry.color }} />
          <span style={{ color: '#94A3B8' }}>{labelMap[entry.dataKey] ?? entry.dataKey}:</span>
          <span className="font-bold text-white">{formatValue(entry.value, unit)}</span>
        </div>
      ))}
    </div>
  );
}

function PieTooltip({
  active, payload, unit,
}: {
  active?: boolean;
  payload?: { name: string; value: number; payload: { color?: string } }[];
  unit?: string;
}) {
  if (!active || !payload?.length) return null;
  const p = payload[0];
  return (
    <div style={tooltipWrapStyle}>
      <div className="flex items-center gap-2">
        <span className="inline-block w-2 h-2 rounded-full shrink-0" style={{ background: p.payload.color }} />
        <span style={{ color: '#94A3B8' }}>{p.name}:</span>
        <span className="font-bold text-white">{formatValue(p.value, unit)}</span>
      </div>
    </div>
  );
}

// ── Pie/donut custom label ────────────────────────────────────────────────────

function PieLabel({
  cx, cy, midAngle, innerRadius, outerRadius, percent, name,
}: {
  cx: number; cy: number; midAngle: number;
  innerRadius: number; outerRadius: number;
  percent: number; name: string;
}) {
  if (percent < 0.04) return null;
  const RADIAN = Math.PI / 180;
  const radius = innerRadius + (outerRadius - innerRadius) * 0.55;
  const x = cx + radius * Math.cos(-midAngle * RADIAN);
  const y = cy + radius * Math.sin(-midAngle * RADIAN);
  return (
    <text
      x={x} y={y}
      textAnchor="middle"
      dominantBaseline="central"
      style={{ fill: '#fff', fontSize: 11, fontWeight: 600, pointerEvents: 'none' }}
    >
      {name.length > 12 ? name.slice(0, 11) + '…' : name}
    </text>
  );
}

// ── Main component ────────────────────────────────────────────────────────────

interface ChartBlockProps {
  spec: ChartSpec;
}

const TYPE_LABELS: Record<ChartSpec['type'], string> = {
  bar:     'Bar Chart',
  bar_h:   'Horizontal Bar',
  line:    'Line Chart',
  area:    'Area Chart',
  pie:     'Pie Chart',
  donut:   'Donut Chart',
  scatter: 'Scatter Plot',
};

export default function ChartBlock({ spec }: ChartBlockProps) {
  const { type, title, subtitle, unit, xKey, yKeys, data } = spec;

  if (!data?.length) {
    return (
      <div
        className="rounded-2xl p-4 text-sm text-center"
        style={{ background: 'rgba(124,58,237,0.05)', color: '#94A3B8', border: '1px solid rgba(124,58,237,0.1)' }}
      >
        No chart data available.
      </div>
    );
  }

  const axisStyle  = { fill: '#64748B', fontSize: 11, fontFamily: 'inherit' };
  const gridProps  = { stroke: 'rgba(226,232,240,0.5)', strokeDasharray: '3 3' };
  const chartH     = spec.height ?? (type === 'pie' || type === 'donut' ? 300 : 240);

  // ── Per-type renderers ──────────────────────────────────────────────────────

  function renderBar() {
    return (
      <BarChart data={data} margin={{ top: 4, right: 8, left: 4, bottom: 4 }}>
        <CartesianGrid {...gridProps} vertical={false} />
        <XAxis dataKey={xKey} tick={axisStyle} tickLine={false} axisLine={false} />
        <YAxis tick={axisStyle} tickLine={false} axisLine={false}
          tickFormatter={v => tickFormatter(v, unit)} width={52} />
        <Tooltip content={<CartesianTooltip unit={unit} yKeys={yKeys} />}
          cursor={{ fill: 'rgba(124,58,237,0.06)' }} />
        {yKeys.length > 1 && <Legend wrapperStyle={{ fontSize: 12, color: '#64748B' }} />}
        {yKeys.map((yk, i) => (
          <Bar key={yk.key} dataKey={yk.key} name={yk.label}
            fill={resolveColor(yk, i)} radius={[6, 6, 0, 0]} maxBarSize={56} />
        ))}
      </BarChart>
    );
  }

  function renderBarH() {
    return (
      <BarChart
        data={data}
        layout="vertical"
        margin={{ top: 4, right: 24, left: 8, bottom: 4 }}
      >
        <CartesianGrid {...gridProps} horizontal={false} />
        <XAxis type="number" tick={axisStyle} tickLine={false} axisLine={false}
          tickFormatter={v => tickFormatter(v, unit)} />
        <YAxis type="category" dataKey={xKey} tick={axisStyle} tickLine={false}
          axisLine={false} width={90} />
        <Tooltip content={<CartesianTooltip unit={unit} yKeys={yKeys} />}
          cursor={{ fill: 'rgba(124,58,237,0.06)' }} />
        {yKeys.length > 1 && <Legend wrapperStyle={{ fontSize: 12, color: '#64748B' }} />}
        {yKeys.map((yk, i) => (
          <Bar key={yk.key} dataKey={yk.key} name={yk.label}
            fill={resolveColor(yk, i)} radius={[0, 6, 6, 0]} maxBarSize={28}>
            <LabelList
              dataKey={yk.key}
              position="right"
              formatter={(v: number) => tickFormatter(v, unit)}
              style={{ fill: '#64748B', fontSize: 11 }}
            />
          </Bar>
        ))}
      </BarChart>
    );
  }

  function renderLine() {
    const tickCount = Math.min(8, data.length);
    return (
      <LineChart data={data} margin={{ top: 4, right: 8, left: 4, bottom: 4 }}>
        <CartesianGrid {...gridProps} />
        <XAxis dataKey={xKey} tick={axisStyle} tickLine={false} axisLine={false}
          interval={Math.ceil(data.length / tickCount) - 1} />
        <YAxis tick={axisStyle} tickLine={false} axisLine={false}
          tickFormatter={v => tickFormatter(v, unit)} width={52} />
        <Tooltip content={<CartesianTooltip unit={unit} yKeys={yKeys} />} />
        {yKeys.length > 1 && <Legend wrapperStyle={{ fontSize: 12, color: '#64748B' }} />}
        <ReferenceLine y={0} stroke="rgba(226,232,240,0.8)" />
        {yKeys.map((yk, i) => {
          const color = resolveColor(yk, i);
          return (
            <Line key={yk.key} type="monotone" dataKey={yk.key} name={yk.label}
              stroke={color} strokeWidth={2} dot={false}
              activeDot={{ r: 4, fill: color, stroke: '#fff', strokeWidth: 2 }} />
          );
        })}
      </LineChart>
    );
  }

  function renderArea() {
    const tickCount = Math.min(8, data.length);
    return (
      <AreaChart data={data} margin={{ top: 4, right: 8, left: 4, bottom: 4 }}>
        <defs>
          {yKeys.map((yk, i) => {
            const color = resolveColor(yk, i);
            return (
              <linearGradient key={yk.key} id={`grad-${yk.key}`} x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%"  stopColor={color} stopOpacity={0.25} />
                <stop offset="95%" stopColor={color} stopOpacity={0.02} />
              </linearGradient>
            );
          })}
        </defs>
        <CartesianGrid {...gridProps} />
        <XAxis dataKey={xKey} tick={axisStyle} tickLine={false} axisLine={false}
          interval={Math.ceil(data.length / tickCount) - 1} />
        <YAxis tick={axisStyle} tickLine={false} axisLine={false}
          tickFormatter={v => tickFormatter(v, unit)} width={52} />
        <Tooltip content={<CartesianTooltip unit={unit} yKeys={yKeys} />} />
        {yKeys.length > 1 && <Legend wrapperStyle={{ fontSize: 12, color: '#64748B' }} />}
        {yKeys.map((yk, i) => {
          const color = resolveColor(yk, i);
          return (
            <Area key={yk.key} type="monotone" dataKey={yk.key} name={yk.label}
              stroke={color} strokeWidth={2} fill={`url(#grad-${yk.key})`}
              dot={false} activeDot={{ r: 4, fill: color }} />
          );
        })}
      </AreaChart>
    );
  }

  function renderPie(isDonut: boolean) {
    const total = data.reduce((s, r) => s + (Number(r.value) || 0), 0);
    const innerR = isDonut ? 70 : 0;
    return (
      <PieChart margin={{ top: 0, right: 0, left: 0, bottom: 0 }}>
        <Pie
          data={data}
          cx="50%"
          cy="50%"
          innerRadius={innerR}
          outerRadius={110}
          paddingAngle={isDonut ? 3 : 1}
          dataKey="value"
          nameKey="name"
          labelLine={false}
          label={isDonut ? undefined : PieLabel}
        >
          {data.map((row, i) => (
            <Cell key={i} fill={rowColor(row, i)} stroke="none" />
          ))}
        </Pie>
        <Tooltip content={<PieTooltip unit={unit} />} />
        <Legend
          layout="vertical"
          align="right"
          verticalAlign="middle"
          iconType="circle"
          iconSize={8}
          wrapperStyle={{ fontSize: 12, color: '#64748B', paddingLeft: 16 }}
          formatter={(value: string) =>
            <span style={{ color: '#374151' }}>{value}</span>
          }
        />
        {isDonut && (
          <text x="50%" y="50%" textAnchor="middle" dominantBaseline="middle">
            <tspan x="50%" dy="-6" style={{ fill: '#0F172A', fontSize: 22, fontWeight: 700 }}>
              {formatValue(total, unit)}
            </tspan>
            <tspan x="50%" dy="20" style={{ fill: '#94A3B8', fontSize: 11 }}>
              Total
            </tspan>
          </text>
        )}
      </PieChart>
    );
  }

  function renderScatter() {
    if (!yKeys.length) return null;
    const yk = yKeys[0];
    const color = resolveColor(yk, 0);
    return (
      <ScatterChart margin={{ top: 4, right: 8, left: 4, bottom: 4 }}>
        <CartesianGrid {...gridProps} />
        <XAxis dataKey={xKey} type="number" name={xKey} tick={axisStyle}
          tickLine={false} axisLine={false}
          tickFormatter={v => tickFormatter(v, unit)} />
        <YAxis dataKey={yk.key} type="number" name={yk.label} tick={axisStyle}
          tickLine={false} axisLine={false}
          tickFormatter={v => tickFormatter(v, unit)} width={52} />
        <Tooltip cursor={{ strokeDasharray: '3 3' }} />
        <Scatter data={data} fill={color} name={yk.label} />
      </ScatterChart>
    );
  }

  function renderChart() {
    switch (type) {
      case 'bar':     return renderBar();
      case 'bar_h':   return renderBarH();
      case 'line':    return renderLine();
      case 'area':    return renderArea();
      case 'pie':     return renderPie(false);
      case 'donut':   return renderPie(true);
      case 'scatter': return renderScatter();
      default:        return renderLine();
    }
  }

  const chartNode = renderChart();
  if (!chartNode) return null;

  return (
    <div
      className="rounded-2xl overflow-hidden mt-4"
      style={{
        background: '#fff',
        border: '1px solid rgba(226,232,240,0.8)',
        boxShadow: '0 1px 3px rgba(0,0,0,0.05), 0 4px 16px rgba(0,0,0,0.03)',
      }}
    >
      {/* Header */}
      <div className="px-5 pt-4 pb-2 flex items-start justify-between gap-3">
        <div>
          <h4 className="font-bold text-[14.5px]" style={{ color: '#0F172A' }}>{title}</h4>
          {subtitle && (
            <p className="text-xs mt-0.5" style={{ color: '#94A3B8' }}>{subtitle}</p>
          )}
        </div>
        <span
          className="text-[10px] font-bold uppercase tracking-widest px-2.5 py-1 rounded-full shrink-0 mt-0.5"
          style={{ background: 'rgba(124,58,237,0.08)', color: '#7C3AED', border: '1px solid rgba(124,58,237,0.15)' }}
        >
          {TYPE_LABELS[type] ?? type}
        </span>
      </div>

      {/* Chart */}
      <div className="px-2 pb-4">
        <ResponsiveContainer width="100%" height={chartH}>
          {chartNode}
        </ResponsiveContainer>
      </div>
    </div>
  );
}
