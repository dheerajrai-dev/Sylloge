import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { FileText, ArrowRight } from 'lucide-react';
import { fetchEntities } from '../api/services';
import { EntitySummary } from '../types';
import { LoadingSpinner } from '../components/common/LoadingSpinner';

export const ReportsListPage: React.FC = () => {
  const [entities, setEntities] = useState<EntitySummary[]>([]);
  const [loading, setLoading] = useState(true);
  const navigate = useNavigate();

  useEffect(() => {
    const loadData = async () => {
      setLoading(true);
      try {
        const data = await fetchEntities();
        setEntities(data);
      } catch (err) {
        console.error(err);
      } finally {
        setLoading(false);
      }
    };
    loadData();
  }, []);

  if (loading) {
    return <LoadingSpinner text="Loading Supervisory Compliance Reports Catalog..." />;
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <div className="flex items-center gap-2 text-xs font-mono text-brand-400 uppercase tracking-widest mb-1">
          <FileText className="w-3.5 h-3.5" />
          Regulatory Export Enclave
        </div>
        <h1 className="text-2xl font-bold tracking-tight text-white">Supervisory Reports Catalog</h1>
        <p className="text-surface-muted text-sm mt-1">
          Export formal supervisory compliance reports, cryptographic SHA-256 Merkle root manifests, and evidence summaries.
        </p>
      </div>

      {/* Reports Entity Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {entities.map((entity) => (
          <div
            key={entity.entity_id}
            className="bg-slate-900 border border-slate-800 rounded-xl p-5 hover:border-brand-500/50 transition-all flex flex-col justify-between space-y-4"
          >
            <div>
              <div className="flex items-center justify-between">
                <span className="text-xs font-mono text-brand-400 px-2 py-0.5 rounded bg-brand-950 border border-brand-800">
                  {entity.entity_code}
                </span>
                <span className="text-xs font-semibold px-2 py-0.5 rounded bg-slate-800 text-slate-300">
                  {entity.sector} • {entity.size_tier}
                </span>
              </div>
              <h3 className="text-lg font-bold text-white mt-3">{entity.name}</h3>
              <p className="text-xs text-slate-400 mt-1">
                Formal supervisory report including composite risk score, execution gap findings, and signed audit manifest.
              </p>
            </div>

            <button
              onClick={() => navigate(`/reports/${entity.entity_id}`)}
              className="w-full flex items-center justify-center gap-2 px-4 py-2.5 rounded-lg bg-brand-600 hover:bg-brand-500 text-white font-medium text-sm transition-all shadow-md shadow-brand-600/20"
            >
              <FileText className="w-4 h-4" />
              Generate Report
              <ArrowRight className="w-4 h-4" />
            </button>
          </div>
        ))}
      </div>
    </div>
  );
};
