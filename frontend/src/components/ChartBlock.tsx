/**
 * ChartBlock – renders a chart spec embedded by the agent inside a ```chart block.
 *
 * Supports three chart types:
 *   • "bar"  – categorical comparisons (e.g. revenue vs EBITDA)
 *   • "line" – time-series (e.g. weekly close price)
 *   • "area" – time-series with filled area
 */

import {
  ResponsiveContainer,
  BarChart, Bar,
  LineChart, Line,
  AreaChart, Area,
  XAxis, YAxis,
  CartesianGrid, Tooltip, Legend,
  ReferenceLine,
} from 'recharts';

// ── Types ─────────────────────────────────────────────────────────────────────

export interface YKeySpec {
  key: string;
  label: string;
  color?: string;
}

export interface ChartSpec {
  type: 'bar' | 'line' | 'area';
  title: string;
  subtitle?: string;
  unit?: string;
  xKey: string;
  yKeys: YKeySpec[];
  data: Record<string, string | number>[];
}

// ── Palette ───────────────────────────────────────────────────────────────────

const DEFAULT_COLORS = [
  '#7C3AED', '#10B981', '#F59E0B', '#EF4444',
  '#06B6D4', '#8B5CF6', '#EC4899', '#84CC16',
];

function resolveColor(spec: YKeySpec, idx: number): string {
  return spec.color ?? DEFAULT_COLORS[idx % DEFAULT_COLORS.length];
}

// ── Formatters ────────────────────────────────────────────────────────────────

function formatValue(value: number | string, unit?: string): string {
  if (typeof value !== 'number') return String(value);
  const num = value;
  let formatted: string;

  if (unit === '$B') {
    formatted = `$${num.toFixed(1)}B`;
  } else if (unit === '$M') {
    formatted = `$${num.toFixed(0)}M`;
  } else if (unit === '%') {
    formatted = `${num.toFixed(2)}%`;
  } else if (unit === '$') {
    formatted = `$${num.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
  } else {
    formatted = num.toLocaleString();
  }
  return formatted;
}

function tickFormatter(value: number | string, unit?: string): string {
  if (typeof value !== 'number') return String(value);
  if (unit === '$B') return `$${value}B`;
  if (unit === '$M') return `$${value}M`;
  if (unit === '%') return `${value}%`;
  if (unit === '$') return `$${value}`;
  return String(value);
}

// ── Custom tooltip ────────────────────────────────────────────────────────────

function CustomTooltip({
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
    <div
      className="rounded-xl px-4 py-3 text-sm"
      style={{
        background: 'rgba(12,14,26,0.92)',
        backdropFilter: 'blur(8px)',
        border: '1px solid rgba(255,255,255,0.1)',
        boxShadow: '0 4px 24px rgba(0,0,0,0.25)',
      }}
    >
      <p className="font-semibold mb-1.5 text-white">{label}</p>
      {payload.map(entry => (
        <div key={entry.dataKey} className="flex items-center gap-2">
          <span
            className="inline-block w-2 h-2 rounded-full shrink-0"
            style={{ background: entry.color }}
          />
          <span style={{ color: '#94A3B8' }}>{labelMap[entry.dataKey] ?? entry.dataKey}:</span>
          <span className="font-bold text-white">{formatValue(entry.value, unit)}</span>
        </div>
      ))}
    </div>
  );
}

// ── Main component ────────────────────────────────────────────────────────────

interface ChartBlockProps {
  spec: ChartSpec;
}

export default function ChartBlock({ spec }: ChartBlockProps) {
  const { type, title, subtitle, unit, xKey, yKeys, data } = spec;

  if (!data?.length || !yKeys?.length) {
    return (
      <div
        className="rounded-2xl p-4 text-sm text-center"
        style={{ background: 'rgba(124,58,237,0.05)', color: '#94A3B8', border: '1px solid rgba(124,58,237,0.1)' }}
      >
        No chart data available.
      </div>
    );
  }

  const axisStyle = { fill: '#64748B', fontSize: 11, fontFamily: 'inherit' };
  const gridProps = { stroke: 'rgba(226,232,240,0.5)', strokeDasharray: '3 3' };

  // X-axis tick count (avoid crowding on line/area charts)
  const xTickCount = type === 'bar' ? undefined : Math.min(8, data.length);

  const sharedChartProps = {
    data,
    margin: { top: 4, right: 8, left: 4, bottom: 4 },
  };

  const sharedAxisProps = {
    xAxis: (
      <XAxis
        dataKey={xKey}
        tick={axisStyle}
        tickLine={false}
        axisLine={false}
        interval={xTickCount ? Math.ceil(data.length / xTickCount) - 1 : 0}
      />
    ),
    yAxis: (
      <YAxis
        tick={axisStyle}
        tickLine={false}
        axisLine={false}
        tickFormatter={(v) => tickFormatter(v, unit)}
        width={52}
      />
    ),
  };

  function renderChart() {
    if (type === 'bar') {
      return (
        <BarChart {...sharedChartProps}>
          <CartesianGrid {...gridProps} vertical={false} />
          {sharedAxisProps.xAxis}
          {sharedAxisProps.yAxis}
          <Tooltip content={<CustomTooltip unit={unit} yKeys={yKeys} />} cursor={{ fill: 'rgba(124,58,237,0.06)' }} />
          {yKeys.length > 1 && <Legend wrapperStyle={{ fontSize: 12, color: '#64748B' }} />}
          {yKeys.map((yk, i) => (
            <Bar
              key={yk.key}
              dataKey={yk.key}
              name={yk.label}
              fill={resolveColor(yk, i)}
              radius={[6, 6, 0, 0]}
              maxBarSize={56}
            />
          ))}
        </BarChart>
      );
    }

    if (type === 'area') {
      return (
        <AreaChart {...sharedChartProps}>
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
          {sharedAxisProps.xAxis}
          {sharedAxisProps.yAxis}
          <Tooltip content={<CustomTooltip unit={unit} yKeys={yKeys} />} />
          {yKeys.length > 1 && <Legend wrapperStyle={{ fontSize: 12, color: '#64748B' }} />}
          {yKeys.map((yk, i) => {
            const color = resolveColor(yk, i);
            return (
              <Area
                key={yk.key}
                type="monotone"
                dataKey={yk.key}
                name={yk.label}
                stroke={color}
                strokeWidth={2}
                fill={`url(#grad-${yk.key})`}
                dot={false}
                activeDot={{ r: 4, fill: color }}
              />
            );
          })}
        </AreaChart>
      );
    }

    // default: line
    return (
      <LineChart {...sharedChartProps}>
        <CartesianGrid {...gridProps} />
        {sharedAxisProps.xAxis}
        {sharedAxisProps.yAxis}
        <Tooltip content={<CustomTooltip unit={unit} yKeys={yKeys} />} />
        {yKeys.length > 1 && <Legend wrapperStyle={{ fontSize: 12, color: '#64748B' }} />}
        <ReferenceLine y={0} stroke="rgba(226,232,240,0.8)" />
        {yKeys.map((yk, i) => {
          const color = resolveColor(yk, i);
          return (
            <Line
              key={yk.key}
              type="monotone"
              dataKey={yk.key}
              name={yk.label}
              stroke={color}
              strokeWidth={2}
              dot={false}
              activeDot={{ r: 4, fill: color, stroke: '#fff', strokeWidth: 2 }}
            />
          );
        })}
      </LineChart>
    );
  }

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
          {type === 'bar' ? 'Bar Chart' : type === 'area' ? 'Area Chart' : 'Line Chart'}
        </span>
      </div>

      {/* Chart */}
      <div className="px-2 pb-4">
        <ResponsiveContainer width="100%" height={240}>
          {renderChart()}
        </ResponsiveContainer>
      </div>
    </div>
  );
}
