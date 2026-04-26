/**
 * Component tests for ChartBlock.tsx
 *
 * ChartBlock renders fenced ```chart JSON``` blocks from agent responses
 * as Recharts visualisations.
 */

import { render, screen } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import ChartBlock from '../components/ChartBlock';

// Mock recharts since jsdom can't render SVG properly
vi.mock('recharts', () => ({
  ResponsiveContainer: ({ children }: any) => <div data-testid="responsive-container">{children}</div>,
  BarChart: ({ children }: any) => <div data-testid="bar-chart">{children}</div>,
  LineChart: ({ children }: any) => <div data-testid="line-chart">{children}</div>,
  AreaChart: ({ children }: any) => <div data-testid="area-chart">{children}</div>,
  PieChart: ({ children }: any) => <div data-testid="pie-chart">{children}</div>,
  Bar: () => <div data-testid="bar" />,
  Line: () => <div data-testid="line" />,
  Area: () => <div data-testid="area" />,
  Pie: () => <div data-testid="pie" />,
  Cell: () => null,
  XAxis: () => null,
  YAxis: () => null,
  CartesianGrid: () => null,
  Tooltip: () => null,
  Legend: () => null,
}));

const barChartSpec = {
  type: 'bar' as const,
  title: 'Apple Annual Revenue',
  subtitle: 'USD Billions',
  unit: '$B',
  xKey: 'name',
  yKeys: [{ key: 'value', label: 'Revenue', color: '#6366F1' }],
  data: [
    { name: 'FY 2021', value: 365.8 },
    { name: 'FY 2022', value: 394.3 },
    { name: 'FY 2023', value: 383.3 },
    { name: 'FY 2024', value: 391.0 },
  ],
};

const lineChartSpec = {
  type: 'line' as const,
  title: 'AAPL Price History',
  unit: '$',
  xKey: 'date',
  yKeys: [{ key: 'close', label: 'Close Price', color: '#10B981' }],
  data: [
    { date: '2024-01', close: 185.5 },
    { date: '2024-02', close: 184.2 },
    { date: '2024-03', close: 171.2 },
  ],
};

describe('ChartBlock', () => {
  it('renders the chart title', () => {
    render(<ChartBlock spec={barChartSpec} />);
    expect(screen.getByText('Apple Annual Revenue')).toBeInTheDocument();
  });

  it('renders the chart subtitle when present', () => {
    render(<ChartBlock spec={barChartSpec} />);
    expect(screen.getByText('USD Billions')).toBeInTheDocument();
  });

  it('renders a bar chart for type="bar"', () => {
    render(<ChartBlock spec={barChartSpec} />);
    expect(screen.getByTestId('bar-chart')).toBeInTheDocument();
  });

  it('renders a line chart for type="line"', () => {
    render(<ChartBlock spec={lineChartSpec} />);
    expect(screen.getByTestId('line-chart')).toBeInTheDocument();
  });

  it('does not render subtitle when absent', () => {
    const spec = { ...barChartSpec, subtitle: undefined };
    render(<ChartBlock spec={spec} />);
    expect(screen.queryByText('USD Billions')).not.toBeInTheDocument();
  });

  it('renders without crashing for empty data array', () => {
    const spec = { ...barChartSpec, data: [] };
    const { container } = render(<ChartBlock spec={spec} />);
    expect(container).toBeTruthy();
  });

  it('renders without crashing for pie chart type', () => {
    const pieSpec = {
      ...barChartSpec,
      type: 'pie' as const,
      title: 'Revenue Breakdown',
    };
    render(<ChartBlock spec={pieSpec} />);
    expect(screen.getByText('Revenue Breakdown')).toBeInTheDocument();
  });
});
