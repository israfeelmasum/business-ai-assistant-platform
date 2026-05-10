import { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';

const BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:9000/api/v1';
const STORAGE_TOKEN_KEY = 'cb_jwt_token';
const STORAGE_USER_KEY  = 'cb_user';
const STORAGE_ORG_KEY   = 'cb_org_id';

function Spinner() {
  return (
    <svg className="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24">
      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z" />
    </svg>
  );
}

export default function CompanyPortal() {
  const navigate = useNavigate();

  // Form state
  const [fullName, setFullName]       = useState('');
  const [email, setEmail]             = useState('');
  const [password, setPassword]       = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [companyName, setCompanyName] = useState('');

  const [loading, setLoading]   = useState(false);
  const [error, setError]       = useState('');
  const [success, setSuccess]   = useState('');

  async function handleSignup(e) {
    e.preventDefault();
    if (password !== confirmPassword) {
      setError('Passwords do not match.');
      return;
    }
    setLoading(true);
    setError('');
    setSuccess('');

    try {
      const res = await fetch(`${BASE_URL}/auth/company-signup`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          full_name:    fullName.trim(),
          email:        email.trim(),
          password,
          company_name: companyName.trim(),
        }),
      });

      if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: res.statusText }));
        throw new Error(err.detail || `HTTP ${res.status}`);
      }

      const data = await res.json();

      // Extract token — API may return it directly or nested
      const accessToken = data?.tokens?.access_token
        || data?.access_token
        || data?.token
        || '';

      if (accessToken) {
        // Persist auth data so the protected routes work immediately
        localStorage.setItem(STORAGE_TOKEN_KEY, accessToken);

        const me = data?.user || data?.me || null;
        if (me) {
          localStorage.setItem(STORAGE_USER_KEY, JSON.stringify(me));
          const oid = me.default_org_id || data?.organization?.id || '';
          if (oid) localStorage.setItem(STORAGE_ORG_KEY, oid);
        }

        setSuccess('Company registered! Redirecting to dashboard…');
        setTimeout(() => navigate('/', { replace: true }), 1200);
      } else {
        // Signup succeeded but no token returned — ask user to log in
        setSuccess('Company registered successfully! Please sign in.');
        setTimeout(() => navigate('/login', { replace: true }), 1500);
      }
    } catch (err) {
      setError(err.message || 'Registration failed. Please try again.');
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-blue-950 to-slate-900 flex items-center justify-center p-4">
      <div className="w-full max-w-md">

        {/* Logo / branding */}
        <div className="text-center mb-8">
          <div className="w-16 h-16 bg-blue-600 rounded-2xl flex items-center justify-center mx-auto mb-4 shadow-lg shadow-blue-600/30">
            <svg className="w-8 h-8 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4" />
            </svg>
          </div>
          <h1 className="text-2xl font-bold text-white">Fellow BOT</h1>
          <p className="text-slate-400 mt-1 text-sm">Register your company to get started</p>
        </div>

        {/* Card */}
        <form
          onSubmit={handleSignup}
          className="bg-white/10 backdrop-blur-xl rounded-2xl p-6 border border-white/10 space-y-4"
        >
          <h2 className="text-white font-semibold text-base mb-1">Create your account</h2>

          {/* Full Name */}
          <div>
            <label className="block text-sm font-medium text-slate-300 mb-1.5">Full Name</label>
            <input
              type="text"
              value={fullName}
              onChange={e => setFullName(e.target.value)}
              placeholder="Jane Smith"
              required
              autoFocus
              className="w-full px-4 py-3 bg-white/10 border border-white/20 rounded-xl text-white
                         placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-blue-500
                         focus:border-transparent text-sm transition"
            />
          </div>

          {/* Email */}
          <div>
            <label className="block text-sm font-medium text-slate-300 mb-1.5">Email Address</label>
            <input
              type="email"
              value={email}
              onChange={e => setEmail(e.target.value)}
              placeholder="jane@company.com"
              required
              autoComplete="email"
              className="w-full px-4 py-3 bg-white/10 border border-white/20 rounded-xl text-white
                         placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-blue-500
                         focus:border-transparent text-sm transition"
            />
          </div>

          {/* Company Name */}
          <div>
            <label className="block text-sm font-medium text-slate-300 mb-1.5">Company Name</label>
            <input
              type="text"
              value={companyName}
              onChange={e => setCompanyName(e.target.value)}
              placeholder="Acme Corp"
              required
              className="w-full px-4 py-3 bg-white/10 border border-white/20 rounded-xl text-white
                         placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-blue-500
                         focus:border-transparent text-sm transition"
            />
          </div>

          {/* Password */}
          <div>
            <label className="block text-sm font-medium text-slate-300 mb-1.5">Password</label>
            <input
              type="password"
              value={password}
              onChange={e => setPassword(e.target.value)}
              placeholder="••••••••"
              required
              autoComplete="new-password"
              className="w-full px-4 py-3 bg-white/10 border border-white/20 rounded-xl text-white
                         placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-blue-500
                         focus:border-transparent text-sm transition"
            />
          </div>

          {/* Confirm Password */}
          <div>
            <label className="block text-sm font-medium text-slate-300 mb-1.5">Confirm Password</label>
            <input
              type="password"
              value={confirmPassword}
              onChange={e => setConfirmPassword(e.target.value)}
              placeholder="••••••••"
              required
              autoComplete="new-password"
              className="w-full px-4 py-3 bg-white/10 border border-white/20 rounded-xl text-white
                         placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-blue-500
                         focus:border-transparent text-sm transition"
            />
          </div>

          {/* Error */}
          {error && (
            <div className="flex items-start gap-2 bg-red-500/20 border border-red-500/30 rounded-lg px-3 py-2">
              <svg className="w-4 h-4 text-red-400 flex-shrink-0 mt-0.5" fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7 4a1 1 0 11-2 0 1 1 0 012 0zm-1-9a1 1 0 00-1 1v4a1 1 0 102 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
              </svg>
              <p className="text-red-300 text-sm">{error}</p>
            </div>
          )}

          {/* Success */}
          {success && (
            <div className="flex items-center gap-2 bg-green-500/20 border border-green-500/30 rounded-lg px-3 py-2">
              <svg className="w-4 h-4 text-green-400 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
              </svg>
              <p className="text-green-300 text-sm">{success}</p>
            </div>
          )}

          {/* Submit */}
          <button
            type="submit"
            disabled={loading || !fullName.trim() || !email.trim() || !companyName.trim() || !password || !confirmPassword}
            className="w-full py-3 bg-blue-600 hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed
                       text-white font-semibold rounded-xl transition-colors text-sm flex items-center justify-center gap-2"
          >
            {loading ? <><Spinner /> Creating account…</> : 'Register Company'}
          </button>

          {/* Sign in link */}
          <p className="text-center text-slate-400 text-sm pt-1">
            Already have an account?{' '}
            <Link to="/login" className="text-blue-400 hover:text-blue-300 font-medium transition-colors">
              Sign in
            </Link>
          </p>
        </form>

        <p className="text-center text-slate-600 text-xs mt-6">
          Fellow BOT SaaS Platform &mdash; Company Registration
        </p>
      </div>
    </div>
  );
}
