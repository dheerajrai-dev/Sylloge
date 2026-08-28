import React from 'react';
import {
  Radar,
  RadarChart,
  PolarGrid,
  PolarAngleAxis,
  PolarRadiusAxis,
  ResponsiveContainer,
  Tooltip,
  Legend,
} from 'recharts';

interface EngineRadarChartProps {
  data: Array<{
    axis: string;
    value: number;
    benchmark: number;
  }>;
  height?: number;
}

export const EngineRadarChart: React.FC<EngineRadarChartProps> = ({ data, height = 280 }) => {
  return (
    <div className="w-full h-full min-h-[240px]">
      <ResponsiveContainer width="100%" height={height}>
        <RadarChart cx="50%" cy="50%" outerRadius="75%" data={data}>
          <PolarGrid stroke="#334155" />
          <PolarAngleAxis
            dataKey="axis"
            tick={{ fill: '#cbd5e1', fontSize: 11 }}
          />
          <PolarRadiusAxis
            angle={30}
            domain={[0, 100]}
            stroke="#64748b"
            tick={{ fontSize: 10, fill: '#64748b' }}
          />
          <Radar
            name="Entity Score"
            dataKey="value"
            stroke="#ef4444"
            fill="#ef4444"
            fillOpacity={0.4}
          />
          <Radar
            name="Cohort Mean Benchmark"
            dataKey="benchmark"
            stroke="#38bdf8"
            fill="#38bdf8"
            fillOpacity={0.2}
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
            verticalAlign="bottom"
            iconType="circle"
            wrapperStyle={{ fontSize: '11px', paddingTop: '10px' }}
          />
        </RadarChart>
      </ResponsiveContainer>
    </div>
  );
};
