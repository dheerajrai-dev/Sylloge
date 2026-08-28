import React from 'react';
import {
  ScatterChart,
  Scatter,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  ReferenceLine,
} from 'recharts';
import { WorklistItem } from '../../types';

interface RiskMatrixScatterProps {
  entities: WorklistItem[];
  height?: number;
  onSelectEntity?: (entityId: string) => void;
}

export const RiskMatrixScatter: React.FC<RiskMatrixScatterProps> = ({
  entities,
  height = 280,
  onSelectEntity,
}) => {
  const data = entities.map((e) => ({
    id: e.entity_id,
    name: e.name,
    code: e.entity_code,
    x: e.execution_gap_score,
    y: e.negative_space_score,
    composite: e.composite_risk_score,
    tier: e.risk_tier,
  }));

  const CustomTooltip = ({ active, payload }: any) => {
    if (active && payload && payload.length) {
      const p = payload[0].payload;
      return (
        <div className="bg-slate-900 border border-slate-700 p-3 rounded-lg shadow-xl text-xs text-slate-100">
          <div className="font-bold text-sm text-white">{p.name} ({p.code})</div>
          <div className="mt-1 text-slate-300">Composite Score: <span className="font-bold text-brand-400">{p.composite}</span></div>
          <div className="text-slate-300">Execution Gap: <span className="font-bold text-red-400">{p.x}</span></div>
          <div className="text-slate-300">Negative Space: <span className="font-bold text-amber-400">{p.y}</span></div>
          <div className="mt-1 text-[11px] text-slate-400">Click dot to inspect entity</div>
        </div>
      );
    }
    return null;
  };

  return (
    <div className="w-full h-full min-h-[240px] relative">
      <ResponsiveContainer width="100%" height={height}>
        <ScatterChart margin={{ top: 20, right: 20, bottom: 20, left: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#334155" opacity={0.5} />
          <XAxis
            type="number"
            dataKey="x"
            name="Execution Gap"
            domain={[0, 100]}
            stroke="#94a3b8"
            fontSize={11}
            label={{ value: 'Execution Gap (45%) →', position: 'bottom', fill: '#94a3b8', fontSize: 11, dy: 10 }}
          />
          <YAxis
            type="number"
            dataKey="y"
            name="Negative Space"
            domain={[0, 100]}
            stroke="#94a3b8"
            fontSize={11}
            label={{ value: 'Negative Space (35%) →', angle: -90, position: 'left', fill: '#94a3b8', fontSize: 11, dx: -10 }}
          />
          <ReferenceLine x={50} stroke="#475569" strokeDasharray="3 3" />
          <ReferenceLine y={50} stroke="#475569" strokeDasharray="3 3" />
          <Tooltip content={<CustomTooltip />} />
          <Scatter
            data={data}
            fill="#ef4444"
            cursor="pointer"
            onClick={(node) => onSelectEntity && onSelectEntity(node.id)}
          />
        </ScatterChart>
      </ResponsiveContainer>
    </div>
  );
};
