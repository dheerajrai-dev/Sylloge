import React from 'react';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from 'recharts';

interface TrendLineChartProps {
  data: Array<{
    date: string;
    composite: number;
    execution_gap?: number;
    negative_space?: number;
    peer_deviation?: number;
  }>;
  height?: number;
}

export const TrendLineChart: React.FC<TrendLineChartProps> = ({ data, height = 260 }) => {
  return (
    <div className="w-full h-full min-h-[220px]">
      <ResponsiveContainer width="100%" height={height}>
        <LineChart data={data} margin={{ top: 10, right: 20, left: -20, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#334155" opacity={0.5} />
          <XAxis
            dataKey="date"
            stroke="#94a3b8"
            fontSize={11}
            tickLine={false}
            dy={8}
          />
          <YAxis
            stroke="#94a3b8"
            fontSize={11}
            domain={[0, 100]}
            tickLine={false}
          />
          <Tooltip
            contentStyle={{
              backgroundColor: '#0f172a',
              borderColor: '#334155',
              borderRadius: '0.5rem',
              color: '#f8fafc',
              fontSize: '12px',
            }}
          />
          <Legend
            verticalAlign="top"
            align="right"
            iconType="circle"
            wrapperStyle={{ fontSize: '11px', paddingBottom: '10px' }}
          />
          <Line
            type="monotone"
            dataKey="composite"
            name="Composite (0-100)"
            stroke="#0284c7"
            strokeWidth={3}
            dot={{ r: 4, fill: '#0284c7' }}
            activeDot={{ r: 6 }}
          />
          {data[0]?.execution_gap !== undefined && (
            <Line
              type="monotone"
              dataKey="execution_gap"
              name="Execution Gap (45%)"
              stroke="#ef4444"
              strokeWidth={1.5}
              strokeDasharray="4 4"
              dot={false}
            />
          )}
          {data[0]?.negative_space !== undefined && (
            <Line
              type="monotone"
              dataKey="negative_space"
              name="Negative Space (35%)"
              stroke="#f59e0b"
              strokeWidth={1.5}
              strokeDasharray="4 4"
              dot={false}
            />
          )}
          {data[0]?.peer_deviation !== undefined && (
            <Line
              type="monotone"
              dataKey="peer_deviation"
              name="Peer Deviation (20%)"
              stroke="#38bdf8"
              strokeWidth={1.5}
              strokeDasharray="4 4"
              dot={false}
            />
          )}
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
};
