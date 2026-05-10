import { Routes, Route, Navigate } from 'react-router-dom';
import { useAuth } from './context/AuthContext';
import Layout from './components/Layout';
import Login from './pages/Login';
import Overview from './pages/Overview';
import DataSources from './pages/DataSources';
import Knowledge from './pages/Knowledge';
import Conversations from './pages/Conversations';
import EscalatedChats from './pages/EscalatedChats';
import Settings from './pages/Settings';
import Integration from './pages/Integration';
import SuperAdmin from './pages/SuperAdmin';
import CompanyPortal from './pages/CompanyPortal';
import Analytics from './pages/Analytics';

function ProtectedRoute({ children }) {
  const { token, user, loading, bootstrapped } = useAuth();
  // Wait for stored-token validation before deciding
  if (!bootstrapped || loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="text-center">
          <div className="w-8 h-8 border-4 border-blue-600 border-t-transparent rounded-full animate-spin mx-auto mb-3" />
          <p className="text-sm text-gray-500">Loading...</p>
        </div>
      </div>
    );
  }
  if (!token || !user) return <Navigate to="/login" replace />;
  return <Layout>{children}</Layout>;
}

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route path="/register" element={<CompanyPortal />} />
      <Route path="/" element={<ProtectedRoute><Overview /></ProtectedRoute>} />
      <Route path="/data-sources" element={<ProtectedRoute><DataSources /></ProtectedRoute>} />
      <Route path="/knowledge" element={<ProtectedRoute><Knowledge /></ProtectedRoute>} />
      <Route path="/conversations" element={<ProtectedRoute><Conversations /></ProtectedRoute>} />
      <Route path="/escalated" element={<ProtectedRoute><EscalatedChats /></ProtectedRoute>} />
      <Route path="/analytics" element={<ProtectedRoute><Analytics /></ProtectedRoute>} />
      <Route path="/settings" element={<ProtectedRoute><Settings /></ProtectedRoute>} />
      <Route path="/integration" element={<ProtectedRoute><Integration /></ProtectedRoute>} />
      <Route path="/super-admin" element={<ProtectedRoute><SuperAdmin /></ProtectedRoute>} />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
