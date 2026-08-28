import React from 'react';
import { NavLink } from 'react-router-dom';
import {
  ShieldAlert,
  LayoutDashboard,
  Building2,
  AlertTriangle,
  UploadCloud,
  FileText,
  History,
  Lock,
} from 'lucide-react';

const navItems = [
  { name: 'Dashboard', path: '/dashboard', icon: LayoutDashboard },
  { name: 'Telemetry Ingestion', path: '/upload', icon: UploadCloud },
  { name: 'Entity Assessment', path: '/entities', icon: Building2 },
  { name: 'Findings Explorer', path: '/findings', icon: AlertTriangle },
  { name: 'Supervisory Reports', path: '/reports', icon: FileText },
  { name: 'Audit Trail', path: '/audit', icon: History },
];

export const Sidebar: React.FC = () => {
  return (
    <aside className="w-64 bg-slate-950 border-r border-surface-border flex flex-col justify-between h-screen sticky top-0 shrink-0 select-none no-print">
      <div>
        {/* Brand Header */}
        <div className="h-16 flex items-center px-6 gap-3 border-b border-surface-border bg-slate-950">
          <div className="w-9 h-9 rounded-lg bg-brand-600 flex items-center justify-center text-white shadow-lg shadow-brand-500/20">
            <ShieldAlert className="w-5 h-5" />
          </div>
          <div>
            <div className="font-bold tracking-tight text-white flex items-center gap-1.5 text-base">
              Sylloge <span className="text-[10px] px-1.5 py-0.5 rounded bg-brand-900/80 text-brand-400 border border-brand-700/50">PLATFORM</span>
            </div>
            <div className="text-[10px] text-surface-muted font-mono tracking-wider uppercase">Air-Gapped SOC Enclave</div>
          </div>
        </div>

        {/* Navigation Items */}
        <nav className="p-3 space-y-1">
          {navItems.map((item) => (
            <NavLink
              key={item.path}
              to={item.path}
              className={({ isActive }) =>
                `flex items-center gap-3 px-3.5 py-2.5 rounded-lg text-sm font-medium transition-all duration-150 ${
                  isActive
                    ? 'bg-brand-600 text-white shadow-md shadow-brand-600/30'
                    : 'text-slate-400 hover:text-slate-100 hover:bg-slate-900'
                }`
              }
            >
              <item.icon className="w-4 h-4 shrink-0" />
              <span>{item.name}</span>
            </NavLink>
          ))}
        </nav>
      </div>

      {/* Enclave Security Status Badge */}
      <div className="p-4 border-t border-surface-border bg-slate-950/80">
        <div className="p-3 rounded-lg border border-slate-800 bg-slate-900/60 flex items-start gap-2.5">
          <Lock className="w-4 h-4 text-emerald-400 mt-0.5 shrink-0" />
          <div>
            <div className="text-xs font-semibold text-slate-200">Air-Gapped Offline</div>
            <div className="text-[11px] text-slate-400 mt-0.5 leading-snug">
              Strict isolation: zero remote CDNs or external network calls.
            </div>
          </div>
        </div>
      </div>
    </aside>
  );
};
