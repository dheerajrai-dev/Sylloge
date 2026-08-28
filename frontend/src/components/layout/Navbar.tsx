import React from 'react';
import { UserCheck, LogOut, Radio } from 'lucide-react';
import { useAuth } from '../../context/AuthContext';

export const Navbar: React.FC = () => {
  const { user, logout } = useAuth();

  return (
    <header className="h-16 border-b border-surface-border bg-slate-950/60 backdrop-blur px-6 flex items-center justify-between sticky top-0 z-40 no-print">
      <div className="flex items-center gap-3">
        <div className="flex items-center gap-2 px-3 py-1 rounded-full bg-emerald-950/50 border border-emerald-800/40 text-emerald-400 text-xs font-mono">
          <Radio className="w-3.5 h-3.5 animate-pulse text-emerald-400" />
          <span>SUPERVISORY ENCLAVE : SECURE</span>
        </div>
      </div>

      <div className="flex items-center gap-4">
        <div className="flex items-center gap-2.5 px-3 py-1.5 rounded-lg border border-surface-border bg-surface-card">
          <div className="w-7 h-7 rounded-full bg-brand-900/60 border border-brand-700 flex items-center justify-center text-brand-300">
            <UserCheck className="w-4 h-4" />
          </div>
          <div className="text-left">
            <div className="text-xs font-semibold text-slate-100">{user?.full_name || user?.username || 'Lead Supervisor'}</div>
            <div className="text-[10px] text-surface-muted font-mono uppercase">{user?.role || 'supervisor'}</div>
          </div>
        </div>

        <button
          onClick={logout}
          title="Sign out of supervisory portal"
          className="p-2 rounded-lg border border-surface-border bg-surface-card text-slate-400 hover:text-red-400 hover:border-red-800/60 hover:bg-red-950/20 transition duration-150"
        >
          <LogOut className="w-4 h-4" />
        </button>
      </div>
    </header>
  );
};
