import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { ShieldAlert, Lock, ArrowRight, KeyRound, Radio } from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { useNotification } from '../context/NotificationContext';
import { LoadingSpinner } from '../components/common/LoadingSpinner';

export const LoginPage: React.FC = () => {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const { login, demoLogin } = useAuth();
  const { notify } = useNotification();
  const navigate = useNavigate();

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!username || !password) {
      setErrorMsg('Please enter both username and password.');
      return;
    }

    setIsSubmitting(true);
    setErrorMsg(null);

    try {
      await login(username, password);
      notify('success', 'Supervisor Authenticated', `Welcome, ${username}`);
      navigate('/dashboard');
    } catch (err: any) {
      setErrorMsg(err.message || 'Authentication failed. Please verify credentials.');
      notify('error', 'Login Failed', err.message || 'Invalid credentials');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleQuickDemo = async () => {
    setIsSubmitting(true);
    setErrorMsg(null);
    try {
      await demoLogin();
      notify('success', 'Demo Supervisor Authenticated', 'Logged in as supervisor');
      navigate('/dashboard');
    } catch (err: any) {
      setErrorMsg(err.message || 'Demo login failed');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="min-h-screen bg-surface flex flex-col justify-center items-center p-4 select-none">
      {/* Air-Gapped Banner */}
      <div className="mb-6 flex items-center gap-2 px-3.5 py-1.5 rounded-full bg-slate-900 border border-slate-700 text-slate-300 text-xs font-mono">
        <Radio className="w-3.5 h-3.5 text-emerald-400 animate-pulse" />
        <span>OFFLINE AIR-GAPPED SOC ENCLAVE : SIH 2026</span>
      </div>

      <div className="w-full max-w-md bg-surface-card border border-surface-border rounded-2xl shadow-2xl overflow-hidden">
        {/* Header */}
        <div className="p-8 pb-6 border-b border-surface-border text-center bg-slate-950/70">
          <div className="w-14 h-14 rounded-2xl bg-brand-600 border border-brand-500 flex items-center justify-center text-white mx-auto shadow-xl shadow-brand-600/30 mb-4">
            <ShieldAlert className="w-7 h-7" />
          </div>
          <h1 className="text-xl font-bold text-white tracking-tight">Sylloge</h1>
          <p className="text-xs text-surface-muted mt-1">Supervisory Cybersecurity Analytics Platform</p>
        </div>

        {/* Form */}
        <form onSubmit={handleLogin} className="p-8 space-y-4">
          {errorMsg && (
            <div className="p-3 rounded-lg bg-red-950/80 border border-red-800 text-red-300 text-xs flex items-start gap-2">
              <Lock className="w-4 h-4 text-red-400 mt-0.5 shrink-0" />
              <span>{errorMsg}</span>
            </div>
          )}

          <div>
            <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-1.5">
              Supervisor Username
            </label>
            <div className="relative">
              <input
                type="text"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                placeholder="supervisor"
                className="w-full bg-slate-950 border border-surface-border rounded-lg px-3.5 py-2.5 text-sm text-slate-100 placeholder-slate-500 focus:outline-none focus:border-brand-500 focus:ring-1 focus:ring-brand-500 transition"
              />
            </div>
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-1.5">
              Passphrase
            </label>
            <div className="relative">
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••••••"
                className="w-full bg-slate-950 border border-surface-border rounded-lg px-3.5 py-2.5 text-sm text-slate-100 placeholder-slate-500 focus:outline-none focus:border-brand-500 focus:ring-1 focus:ring-brand-500 transition"
              />
            </div>
          </div>

          <button
            type="submit"
            disabled={isSubmitting}
            className="w-full mt-2 py-2.5 px-4 bg-brand-600 hover:bg-brand-500 text-white rounded-lg font-medium text-sm flex items-center justify-center gap-2 shadow-lg shadow-brand-600/30 transition duration-150 disabled:opacity-50"
          >
            {isSubmitting ? (
              <LoadingSpinner size="sm" />
            ) : (
              <>
                <span>Authenticate Enclave Session</span>
                <ArrowRight className="w-4 h-4" />
              </>
            )}
          </button>

          {/* Quick Demo Fill Button */}
          <div className="pt-3 border-t border-surface-border">
            <button
              type="button"
              onClick={handleQuickDemo}
              disabled={isSubmitting}
              className="w-full py-2 px-3 rounded-lg border border-slate-700 bg-slate-900/80 hover:bg-slate-850 hover:border-slate-600 text-slate-300 text-xs font-mono flex items-center justify-center gap-2 transition"
            >
              <KeyRound className="w-3.5 h-3.5 text-brand-400" />
              <span>Quick Demo Fill (Supervisor)</span>
            </button>
          </div>
        </form>
      </div>

      <div className="mt-6 text-xs text-surface-muted font-mono">
        SIH 2026 Problem Statement 26157 • Zero Outbound Telemetry
      </div>
    </div>
  );
};
