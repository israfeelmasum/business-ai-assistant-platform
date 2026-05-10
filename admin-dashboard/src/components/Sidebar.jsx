import { NavLink } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';

const NAV_ITEMS = [
  { path: '/', label: 'Overview', icon: '📊' },
  { path: '/data-sources', label: 'Data Sources', icon: '🔄' },
  { path: '/knowledge', label: 'Knowledge Base', icon: '🧠' },
  { path: '/conversations', label: 'Conversations', icon: '💬' },
  { path: '/escalated', label: 'Escalated Chats', icon: '🚨' },
  { path: '/analytics', label: 'Analytics',       icon: '📈' },
  { path: '/settings', label: 'Settings', icon: '⚙️' },
  { path: '/integration', label: 'Integration', icon: '🔗' },
];

export default function Sidebar() {
  const { user, logout } = useAuth();
  const isSuperAdmin = user?.role === 'super_admin';

  return (
    <aside className="w-64 bg-gradient-to-b from-slate-900 via-slate-800 to-slate-900 text-white flex flex-col min-h-screen fixed left-0 top-0">
      {/* Logo */}
      <div className="p-5 border-b border-slate-700">
        <h1 className="text-lg font-bold tracking-tight">AI Chatbot</h1>
        <p className="text-xs text-slate-400 mt-1 truncate">
          {isSuperAdmin ? '⚡ Platform Admin' : 'Admin Dashboard'}
        </p>
      </div>

      {/* Navigation */}
      <nav className="flex-1 py-4 px-3 space-y-1 overflow-y-auto">
        {/* Super Admin section — only visible to super_admin */}
        {isSuperAdmin && (
          <>
            <p className="px-3 pt-2 pb-1 text-xs font-semibold text-slate-500 uppercase tracking-wider">
              Platform
            </p>
            <NavLink
              to="/super-admin"
              className={({ isActive }) =>
                `flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors ${
                  isActive
                    ? 'bg-purple-600 text-white shadow-lg shadow-purple-600/20'
                    : 'text-slate-300 hover:bg-slate-700/50 hover:text-white'
                }`
              }
            >
              <span className="text-base">🏢</span>
              All Companies
            </NavLink>
            <div className="border-t border-slate-700 my-2" />
            <p className="px-3 pt-1 pb-1 text-xs font-semibold text-slate-500 uppercase tracking-wider">
              My Org
            </p>
          </>
        )}

        {NAV_ITEMS.map(item => (
          <NavLink
            key={item.path}
            to={item.path}
            end={item.path === '/'}
            className={({ isActive }) =>
              `flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors ${
                isActive
                  ? 'bg-blue-600 text-white shadow-lg shadow-blue-600/20'
                  : 'text-slate-300 hover:bg-slate-700/50 hover:text-white'
              }`
            }
          >
            <span className="text-base">{item.icon}</span>
            {item.label}
          </NavLink>
        ))}
      </nav>

      {/* Footer */}
      <div className="p-4 border-t border-slate-700">
        {user && (
          <div className="mb-3 px-1">
            <p className="text-xs text-white font-medium truncate">{user.full_name}</p>
            <p className="text-xs text-slate-400 truncate">{user.email}</p>
            {isSuperAdmin && (
              <span className="inline-block mt-1 px-2 py-0.5 bg-purple-600/30 text-purple-300 text-xs rounded-full">
                super_admin
              </span>
            )}
          </div>
        )}
        <div className="flex items-center gap-2 mb-3">
          <div className="w-2 h-2 bg-green-400 rounded-full animate-pulse" />
          <span className="text-xs text-slate-400">Online</span>
        </div>
        <button
          onClick={logout}
          className="w-full text-left text-sm text-slate-400 hover:text-red-400 transition-colors"
        >
          Logout
        </button>
      </div>
    </aside>
  );
}
