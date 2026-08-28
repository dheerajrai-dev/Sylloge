import React, { createContext, useContext, useState, useCallback } from 'react';
import { CheckCircle, AlertTriangle, XCircle, Info, X } from 'lucide-react';

export type NotificationType = 'success' | 'warning' | 'error' | 'info';

export interface NotificationItem {
  id: string;
  type: NotificationType;
  title: string;
  message?: string;
}

interface NotificationContextType {
  notifications: NotificationItem[];
  notify: (type: NotificationType, title: string, message?: string) => void;
  removeNotification: (id: string) => void;
}

const NotificationContext = createContext<NotificationContextType | undefined>(undefined);

export const NotificationProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [notifications, setNotifications] = useState<NotificationItem[]>([]);

  const removeNotification = useCallback((id: string) => {
    setNotifications((prev) => prev.filter((n) => n.id !== id));
  }, []);

  const notify = useCallback(
    (type: NotificationType, title: string, message?: string) => {
      const id = Math.random().toString(36).substring(2, 9);
      const item: NotificationItem = { id, type, title, message };
      setNotifications((prev) => [...prev, item]);

      setTimeout(() => {
        removeNotification(id);
      }, 5000);
    },
    [removeNotification]
  );

  return (
    <NotificationContext.Provider value={{ notifications, notify, removeNotification }}>
      {children}
      <div className="fixed bottom-4 right-4 z-50 flex flex-col gap-2 max-w-sm w-full no-print">
        {notifications.map((n) => {
          let bg = 'bg-surface-card border-surface-border text-slate-100';
          let icon = <Info className="w-5 h-5 text-sky-400 shrink-0" />;

          if (n.type === 'success') {
            bg = 'bg-slate-900 border-emerald-500/50 text-emerald-100';
            icon = <CheckCircle className="w-5 h-5 text-emerald-400 shrink-0" />;
          } else if (n.type === 'warning') {
            bg = 'bg-slate-900 border-amber-500/50 text-amber-100';
            icon = <AlertTriangle className="w-5 h-5 text-amber-400 shrink-0" />;
          } else if (n.type === 'error') {
            bg = 'bg-slate-900 border-red-500/50 text-red-100';
            icon = <XCircle className="w-5 h-5 text-red-400 shrink-0" />;
          }

          return (
            <div
              key={n.id}
              className={`flex items-start gap-3 p-3.5 rounded-lg border shadow-xl transition-all duration-300 ${bg}`}
            >
              {icon}
              <div className="flex-1">
                <div className="text-sm font-semibold">{n.title}</div>
                {n.message && <div className="text-xs text-slate-300 mt-0.5">{n.message}</div>}
              </div>
              <button
                onClick={() => removeNotification(n.id)}
                className="text-slate-400 hover:text-white"
              >
                <X className="w-4 h-4" />
              </button>
            </div>
          );
        })}
      </div>
    </NotificationContext.Provider>
  );
};

export const useNotification = () => {
  const ctx = useContext(NotificationContext);
  if (!ctx) {
    throw new Error('useNotification must be used within a NotificationProvider');
  }
  return ctx;
};
