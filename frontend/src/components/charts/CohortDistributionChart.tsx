import React from 'react';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Cell,
  ReferenceLine,
} from 'recharts';

interface CohortDistributionChartProps {
  data: Array<{
    name: string;
    score: number;
    tier: string;
  }>;
  meanScore?: number;
  height?: number;
}

export const CohortDistributionChart: React.FC<CohortDistributionChartProps> = ({
  data,
  meanScore,
  height = 240,
}) => {
  return (
    <div className="w-full h-full min-h-[200px]">
      <ResponsiveContainer width="100%" height={height}>
        <BarChart data={data} margin={{ top: 10, right: 20, left: -20, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#334155" opacity={0.5} />
          <XAxis
            dataKey="name"
            stroke="#94a3b8"
            fontSize={10}
            tickLine={false}
            dy={5}
            interval={0}
            angle={-15}
            textAnchor="end"
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
          {meanScore !== undefined && (
            <ReferenceLine y={meanScore} stroke="#38bdf8" strokeDasharray="3 3" />
          )}
          <Bar dataKey="score" name="Risk Score" radius={[4, 4, 0, 0]}>
            {data.map((entry, index) => {
              let fill = '#10b981';
              if (entry.score >= 75) fill = '#ef4444';
              else if (entry.score >= 50) fill = '#f59e0b';
              else if (entry.score >= 25) fill = '#38bdf8';
              return <Cell key={`cell-${index}`} fill={fill} />;
            })}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
};
