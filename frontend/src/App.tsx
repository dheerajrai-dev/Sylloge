import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider } from './context/AuthContext';
import { NotificationProvider } from './context/NotificationContext';
import { AppLayout } from './components/layout/AppLayout';

import { LoginPage } from './pages/LoginPage';
import { DashboardPage } from './pages/DashboardPage';
import { EntityRankingPage } from './pages/EntityRankingPage';
import { EntityDetailPage } from './pages/EntityDetailPage';
import { FindingsListPage } from './pages/FindingsListPage';
import { CaseDrillDownPage } from './pages/CaseDrillDownPage';
import { UploadWorkflowPage } from './pages/UploadWorkflowPage';
import { ReportsListPage } from './pages/ReportsListPage';
import { ReportExportPage } from './pages/ReportExportPage';
import { AuditTrailPage } from './pages/AuditTrailPage';

export const App: React.FC = () => {
  return (
    <BrowserRouter>
      <AuthProvider>
        <NotificationProvider>
          <Routes>
            <Route path="/login" element={<LoginPage />} />

            <Route element={<AppLayout />}>
              <Route path="/" element={<Navigate to="/dashboard" replace />} />
              <Route path="/dashboard" element={<DashboardPage />} />
              <Route path="/entities" element={<EntityRankingPage />} />
              <Route path="/entities/:entityId" element={<EntityDetailPage />} />
              <Route path="/findings" element={<FindingsListPage />} />
              <Route path="/findings/:findingId" element={<CaseDrillDownPage />} />
              <Route path="/upload" element={<UploadWorkflowPage />} />
              <Route path="/reports" element={<ReportsListPage />} />
              <Route path="/reports/:entityId" element={<ReportExportPage />} />
              <Route path="/audit" element={<AuditTrailPage />} />
            </Route>

            <Route path="*" element={<Navigate to="/dashboard" replace />} />
          </Routes>
        </NotificationProvider>
      </AuthProvider>
    </BrowserRouter>
  );
};

export default App;
