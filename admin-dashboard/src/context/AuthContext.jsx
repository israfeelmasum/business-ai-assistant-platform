import { createContext, useContext, useState, useEffect, useMemo } from 'react';
import { createApiClient, loginRequest } from '../api/client';

const AuthContext = createContext(null);

const STORAGE_TOKEN_KEY = 'cb_jwt_token';
const STORAGE_USER_KEY  = 'cb_user';
const STORAGE_ORG_KEY   = 'cb_org_id';

export function AuthProvider({ children }) {
  const [token, setToken]   = useState(() => localStorage.getItem(STORAGE_TOKEN_KEY) || '');
  const [user, setUser]     = useState(() => {
    try { return JSON.parse(localStorage.getItem(STORAGE_USER_KEY)) || null; } catch { return null; }
  });
  const [orgId, setOrgId]   = useState(() => localStorage.getItem(STORAGE_ORG_KEY) || '');
  const [loading, setLoading] = useState(false);
  const [error, setError]   = useState('');
  const [bootstrapped, setBootstrapped] = useState(false);
  const [userOrgs, setUserOrgs] = useState([]);

  // Re-create api client whenever token changes
  const api = useMemo(() => token ? createApiClient(token) : null, [token]);

  // On mount: if we have a stored token but no user, re-fetch /auth/me to validate
  useEffect(() => {
    async function init() {
      if (token && !user) {
        try {
          const tempApi = createApiClient(token);
          const me = await tempApi.get('/auth/me');
          applyUser(me);
        } catch {
          // Token expired / invalid — clear storage
          clearAuth();
        }
      }
      setBootstrapped(true);
    }
    init();
  }, []); // run once on mount

  // Fetch user's org memberships whenever api is available
  useEffect(() => {
    if (!api) return;
    api.get('/organizations').then(data => {
      const list = Array.isArray(data) ? data : data?.organizations || data?.items || [];
      setUserOrgs(list);
    }).catch(() => {});
  }, [api]);

  function applyUser(me) {
    setUser(me);
    const oid = me.default_org_id || '';
    setOrgId(oid);
    localStorage.setItem(STORAGE_USER_KEY, JSON.stringify(me));
    localStorage.setItem(STORAGE_ORG_KEY, oid);
  }

  function clearAuth() {
    setToken('');
    setUser(null);
    setOrgId('');
    setUserOrgs([]);
    localStorage.removeItem(STORAGE_TOKEN_KEY);
    localStorage.removeItem(STORAGE_USER_KEY);
    localStorage.removeItem(STORAGE_ORG_KEY);
  }

  function switchOrg(newOrgId) {
    setOrgId(newOrgId);
    localStorage.setItem(STORAGE_ORG_KEY, newOrgId);
  }

  async function login(email, password) {
    setLoading(true);
    setError('');
    try {
      // 1. Exchange credentials for tokens
      const data = await loginRequest(email, password);
      const accessToken = data?.tokens?.access_token || data?.access_token || '';
      if (!accessToken) throw new Error('No access token returned');

      // 2. Store token first so createApiClient can use it
      setToken(accessToken);
      localStorage.setItem(STORAGE_TOKEN_KEY, accessToken);

      // 3. Fetch user profile
      const tempApi = createApiClient(accessToken);
      const me = await tempApi.get('/auth/me');
      applyUser(me);

      return true;
    } catch (e) {
      setError(e.message || 'Login failed');
      clearAuth();
      return false;
    } finally {
      setLoading(false);
    }
  }

  function logout() {
    clearAuth();
  }

  return (
    <AuthContext.Provider value={{ token, user, orgId, api, login, logout, loading, error, bootstrapped, userOrgs, switchOrg }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used inside AuthProvider');
  return ctx;
}
