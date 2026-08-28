import React, { useEffect, useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import {
  Search,
  Plus,
  FileText,
  ArrowRight,
  Building2,
  BarChart3,
} from 'lucide-react';
import { createEntity, fetchWorklist } from '../api/services';
import { WorklistItem } from '../types';
import { RiskBadge } from '../components/common/RiskBadge';
import { Modal } from '../components/common/Modal';
import { LoadingSpinner } from '../components/common/LoadingSpinner';
import { useNotification } from '../context/NotificationContext';
import { PeerBenchmarksPage } from './PeerBenchmarksPage';

export const EntityRankingPage: React.FC = () => {
  const [searchParams, setSearchParams] = useSearchParams();
  const initialTab = searchParams.get('tab') === 'benchmarks' ? 'benchmarks' : 'registry';
  const [activeTab, setActiveTab] = useState<'registry' | 'benchmarks'>(initialTab);

  const [entities, setEntities] = useState<WorklistItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [sectorFilter, setSectorFilter] = useState('ALL');
  const [tierFilter, setTierFilter] = useState('ALL');
  const [riskFilter, setRiskFilter] = useState('ALL');

  // Modal State
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [newCode, setNewCode] = useState('');
  const [newName, setNewName] = useState('');
  const [newSector, setNewSector] = useState('Banking');
  const [newTier, setNewTier] = useState('Tier-1');
  const [newEmail, setNewEmail] = useState('');
  const [submitting, setSubmitting] = useState(false);

  const navigate = useNavigate();
  const { notify } = useNotification();

  const handleTabChange = (tab: 'registry' | 'benchmarks') => {
    setActiveTab(tab);
    if (tab === 'benchmarks') {
      setSearchParams({ tab: 'benchmarks' });
    } else {
      setSearchParams({});
    }
  };

  const loadEntities = async () => {
    setLoading(true);
    try {
      const data = await fetchWorklist();
      setEntities(data);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadEntities();
  }, []);

  const handleCreateEntity = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newCode || !newName) return;

    setSubmitting(true);
    try {
      await createEntity({
        entity_code: newCode,
        name: newName,
        sector: newSector,
        size_tier: newTier,
        contact_email: newEmail || undefined,
      });
      notify('success', 'Entity Registered', `Created ${newName} (${newCode})`);
      setIsModalOpen(false);
      setNewCode('');
      setNewName('');
      loadEntities();
    } catch (err: any) {
      notify('error', 'Registration Failed', err.message || 'Failed to create entity');
    } finally {
      setSubmitting(false);
    }
  };

  // Filter logic
  const filteredEntities = entities.filter((e) => {
    const matchesSearch =
      search === '' ||
      e.name.toLowerCase().includes(search.toLowerCase()) ||
      e.entity_code.toLowerCase().includes(search.toLowerCase());

    const matchesSector = sectorFilter === 'ALL' || e.sector === sectorFilter;
    const matchesTier = tierFilter === 'ALL' || e.size_tier === tierFilter;
    const matchesRisk = riskFilter === 'ALL' || e.risk_tier.toUpperCase() === riskFilter.toUpperCase();

    return matchesSearch && matchesSector && matchesTier && matchesRisk;
  });

  return (
    <div className="space-y-6">
      {/* Sub-Tabs: Entity Assessment View Switcher */}
      <div className="flex border-b border-surface-border gap-2">
        <button
          onClick={() => handleTabChange('registry')}
          className={`px-4 py-2.5 text-xs font-semibold border-b-2 transition-all flex items-center gap-2 ${
            activeTab === 'registry'
              ? 'border-brand-500 text-brand-400 bg-brand-950/20 rounded-t-lg'
              : 'border-transparent text-slate-400 hover:text-slate-200'
          }`}
        >
          <Building2 className="w-4 h-4" />
          <span>Entity Registry & Rankings</span>
        </button>
        <button
          onClick={() => handleTabChange('benchmarks')}
          className={`px-4 py-2.5 text-xs font-semibold border-b-2 transition-all flex items-center gap-2 ${
            activeTab === 'benchmarks'
              ? 'border-brand-500 text-brand-400 bg-brand-950/20 rounded-t-lg'
              : 'border-transparent text-slate-400 hover:text-slate-200'
          }`}
        >
          <BarChart3 className="w-4 h-4" />
          <span>Peer Cohort Benchmarks</span>
        </button>
      </div>

      {activeTab === 'benchmarks' ? (
        <PeerBenchmarksPage />
      ) : (
        <>
          {/* Header */}
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
            <div>
              <h1 className="text-2xl font-bold text-white tracking-tight">Supervised Entity Ranking Registry</h1>
              <p className="text-xs text-surface-muted mt-1">
                Complete multi-sector entity directory with composite and tripartite sub-score evaluations.
              </p>
            </div>
            <div className="flex items-center gap-3">
              <button
                onClick={() => setIsModalOpen(true)}
                className="flex items-center gap-2 px-4 py-2 bg-brand-600 hover:bg-brand-500 rounded-lg text-xs font-semibold text-white shadow-lg shadow-brand-600/30 transition"
              >
                <Plus className="w-4 h-4" />
                <span>Register New Entity</span>
              </button>
            </div>
          </div>

      {/* Filter Toolbar */}
      <div className="bg-surface-card border border-surface-border rounded-xl p-4 shadow-lg flex flex-col md:flex-row gap-3 items-center justify-between">
        {/* Search */}
        <div className="relative flex-1 w-full md:max-w-md">
          <Search className="w-4 h-4 text-slate-400 absolute left-3.5 top-3" />
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search entities by name or code (e.g. Apex, ENT-BANK-01)..."
            className="w-full bg-slate-950 border border-surface-border rounded-lg pl-10 pr-4 py-2 text-xs text-slate-100 placeholder-slate-500 focus:outline-none focus:border-brand-500"
          />
        </div>

        {/* Dropdowns */}
        <div className="flex items-center gap-3 w-full md:w-auto overflow-x-auto">
          <select
            value={sectorFilter}
            onChange={(e) => setSectorFilter(e.target.value)}
            className="bg-slate-950 border border-surface-border rounded-lg px-3 py-2 text-xs text-slate-300 focus:outline-none focus:border-brand-500"
          >
            <option value="ALL">All Sectors</option>
            <option value="Banking">Banking</option>
            <option value="Energy">Energy</option>
            <option value="Healthcare">Healthcare</option>
            <option value="Telecom">Telecom</option>
            <option value="Government">Government</option>
            <option value="Fintech">Fintech</option>
            <option value="Defense">Defense</option>
          </select>

          <select
            value={tierFilter}
            onChange={(e) => setTierFilter(e.target.value)}
            className="bg-slate-950 border border-surface-border rounded-lg px-3 py-2 text-xs text-slate-300 focus:outline-none focus:border-brand-500"
          >
            <option value="ALL">All Tiers</option>
            <option value="Tier-1">Tier-1 (Large)</option>
            <option value="Tier-2">Tier-2 (Medium)</option>
            <option value="Tier-3">Tier-3 (Small)</option>
          </select>

          <select
            value={riskFilter}
            onChange={(e) => setRiskFilter(e.target.value)}
            className="bg-slate-950 border border-surface-border rounded-lg px-3 py-2 text-xs text-slate-300 focus:outline-none focus:border-brand-500"
          >
            <option value="ALL">All Risk Bands</option>
            <option value="CRITICAL">Critical (≥75)</option>
            <option value="ELEVATED">Elevated (50-74)</option>
            <option value="GUARDED">Guarded (25-49)</option>
            <option value="LOW">Low (&lt;25)</option>
          </select>
        </div>
      </div>

      {/* Table */}
      <div className="bg-surface-card border border-surface-border rounded-xl shadow-xl overflow-hidden">
        {loading ? (
          <div className="py-16">
            <LoadingSpinner size="lg" text="Loading Entity Rankings..." />
          </div>
        ) : filteredEntities.length === 0 ? (
          <div className="py-16 text-center text-slate-400 text-xs">
            No regulated entities match the active filters.
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead>
                <tr className="bg-slate-950/80 border-b border-surface-border text-surface-muted uppercase text-[10px] tracking-wider">
                  <th className="py-3 px-4 font-semibold">Entity</th>
                  <th className="py-3 px-4 font-semibold">Sector / Tier</th>
                  <th className="py-3 px-4 font-semibold">Composite Score</th>
                  <th className="py-3 px-4 font-semibold">45% Gap Score</th>
                  <th className="py-3 px-4 font-semibold">35% Negative Space</th>
                  <th className="py-3 px-4 font-semibold">20% Peer Dev</th>
                  <th className="py-3 px-4 font-semibold">Open Findings</th>
                  <th className="py-3 px-4 font-semibold text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-surface-border/60">
                {filteredEntities.map((ent) => (
                  <tr key={ent.entity_id} className="hover:bg-slate-900/50 transition">
                    <td className="py-3.5 px-4">
                      <div className="font-bold text-slate-100 text-sm">{ent.name}</div>
                      <div className="text-[11px] font-mono text-slate-400">{ent.entity_code}</div>
                    </td>
                    <td className="py-3.5 px-4">
                      <span className="px-2.5 py-1 rounded-md text-[11px] bg-slate-900 border border-slate-800 text-slate-200">
                        {ent.sector} • {ent.size_tier}
                      </span>
                    </td>
                    <td className="py-3.5 px-4">
                      <div className="flex items-center gap-2">
                        <span className="font-mono font-bold text-sm text-slate-100">{ent.composite_risk_score}</span>
                        <RiskBadge level={ent.risk_tier} size="sm" showDot={false} />
                      </div>
                    </td>
                    <td className="py-3.5 px-4 font-mono font-semibold text-red-400">
                      {ent.execution_gap_score}
                    </td>
                    <td className="py-3.5 px-4 font-mono font-semibold text-amber-400">
                      {ent.negative_space_score}
                    </td>
                    <td className="py-3.5 px-4 font-mono font-semibold text-sky-400">
                      {ent.peer_deviation_score}
                    </td>
                    <td className="py-3.5 px-4 font-mono text-slate-300">
                      {ent.open_findings_count} findings
                    </td>
                    <td className="py-3.5 px-4 text-right space-x-2">
                      <button
                        onClick={() => navigate(`/entities/${ent.entity_id}`)}
                        className="px-2.5 py-1.5 rounded-lg bg-slate-900 hover:bg-brand-600 hover:text-white border border-slate-700 text-slate-300 text-xs font-medium inline-flex items-center gap-1 transition"
                      >
                        <span>Drilldown</span>
                        <ArrowRight className="w-3 h-3" />
                      </button>
                      <button
                        onClick={() => navigate(`/reports/${ent.entity_id}`)}
                        title="Export Structured Report"
                        className="px-2.5 py-1.5 rounded-lg bg-slate-900 hover:bg-slate-800 border border-slate-700 text-slate-400 hover:text-slate-200 text-xs font-medium inline-flex items-center gap-1 transition"
                      >
                        <FileText className="w-3.5 h-3.5" />
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
      </>
      )}

      {/* Register Entity Modal */}
      <Modal isOpen={isModalOpen} onClose={() => setIsModalOpen(false)} title="Register Supervised Entity">
        <form onSubmit={handleCreateEntity} className="space-y-4">
          <div>
            <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-1">
              Entity Code (Unique ID)
            </label>
            <input
              type="text"
              required
              value={newCode}
              onChange={(e) => setNewCode(e.target.value.toUpperCase())}
              placeholder="BANK_ALPHA"
              className="w-full bg-slate-950 border border-surface-border rounded-lg px-3 py-2 text-xs text-slate-100 font-mono focus:outline-none focus:border-brand-500"
            />
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-1">
              Organization Name
            </label>
            <input
              type="text"
              required
              value={newName}
              onChange={(e) => setNewName(e.target.value)}
              placeholder="Apex National Bank"
              className="w-full bg-slate-950 border border-surface-border rounded-lg px-3 py-2 text-xs text-slate-100 focus:outline-none focus:border-brand-500"
            />
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-1">
                Sector
              </label>
              <select
                value={newSector}
                onChange={(e) => setNewSector(e.target.value)}
                className="w-full bg-slate-950 border border-surface-border rounded-lg px-3 py-2 text-xs text-slate-300 focus:outline-none focus:border-brand-500"
              >
                <option value="Banking">Banking</option>
                <option value="Energy">Energy</option>
                <option value="Healthcare">Healthcare</option>
                <option value="Telecom">Telecom</option>
                <option value="Government">Government</option>
                <option value="Fintech">Fintech</option>
                <option value="Defense">Defense</option>
              </select>
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-1">
                Size Tier
              </label>
              <select
                value={newTier}
                onChange={(e) => setNewTier(e.target.value)}
                className="w-full bg-slate-950 border border-surface-border rounded-lg px-3 py-2 text-xs text-slate-300 focus:outline-none focus:border-brand-500"
              >
                <option value="Tier-1">Tier-1 (Large)</option>
                <option value="Tier-2">Tier-2 (Medium)</option>
                <option value="Tier-3">Tier-3 (Small)</option>
              </select>
            </div>
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-1">
              Contact / SOC Email
            </label>
            <input
              type="email"
              value={newEmail}
              onChange={(e) => setNewEmail(e.target.value)}
              placeholder="soc@organization.internal"
              className="w-full bg-slate-950 border border-surface-border rounded-lg px-3 py-2 text-xs text-slate-100 focus:outline-none focus:border-brand-500"
            />
          </div>

          <div className="pt-3 flex justify-end gap-2 border-t border-surface-border">
            <button
              type="button"
              onClick={() => setIsModalOpen(false)}
              className="px-4 py-2 rounded-lg bg-slate-900 border border-surface-border text-xs text-slate-300 hover:text-white"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={submitting}
              className="px-4 py-2 bg-brand-600 hover:bg-brand-500 rounded-lg text-xs font-semibold text-white shadow-lg shadow-brand-600/30"
            >
              {submitting ? 'Saving...' : 'Register Entity'}
            </button>
          </div>
        </form>
      </Modal>
    </div>
  );
};
