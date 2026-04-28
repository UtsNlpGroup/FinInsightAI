import { useState, type FormEvent } from 'react';
import { BarChart3, Eye, EyeOff, ArrowRight, AlertCircle } from 'lucide-react';
import { useAuth } from '../context/AuthContext';

type Mode = 'signin' | 'signup';

export default function Login() {
  const { signIn, signUp } = useAuth();
  const [mode,     setMode]     = useState<Mode>('signin');
  const [email,    setEmail]    = useState('');
  const [password, setPassword] = useState('');
  const [showPw,   setShowPw]   = useState(false);
  const [error,    setError]    = useState('');
  const [info,     setInfo]     = useState('');
  const [loading,  setLoading]  = useState(false);

  const toggle = () => { setMode(m => m === 'signin' ? 'signup' : 'signin'); setError(''); setInfo(''); };

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError('');
    setInfo('');
    if (!email || !password) { setError('Please enter your email and password.'); return; }
    setLoading(true);

    const err = mode === 'signin'
      ? await signIn(email, password)
      : await signUp(email, password);

    setLoading(false);

    if (err) {
      setError(err.message);
    } else if (mode === 'signup') {
      setInfo('Check your email for a confirmation link, then sign in.');
      setMode('signin');
    }
    // If signIn succeeded, AuthContext updates user → App re-renders
  };

  return (
    <div
      className="min-h-screen flex items-center justify-center px-4"
      style={{ background: 'linear-gradient(135deg, #F0F4FF 0%, #FAF5FF 50%, #FFF0F7 100%)' }}
    >
      <div
        className="w-full max-w-sm rounded-2xl p-8"
        style={{
          background: '#FFFFFF',
          boxShadow: '0 4px 32px rgba(79,70,229,0.1)',
          border: '1px solid #E5E7EB',
        }}
      >
        {/* Logo */}
        <div className="flex flex-col items-center mb-8">
          <div
            className="w-12 h-12 rounded-xl flex items-center justify-center mb-3"
            style={{ background: 'linear-gradient(135deg, #4F46E5, #7C3AED)' }}
          >
            <BarChart3 size={24} color="#fff" strokeWidth={2.5} />
          </div>
          <h1 className="text-2xl font-bold" style={{ color: '#111827', letterSpacing: '-0.5px' }}>
            FinSight AI
          </h1>
          <p className="text-sm mt-1" style={{ color: '#6B7280' }}>
            {mode === 'signin' ? 'Welcome back – sign in to continue' : 'Create your account'}
          </p>
        </div>

        {/* Form */}
        <form onSubmit={handleSubmit} className="flex flex-col gap-4">
          {/* Email */}
          <div className="flex flex-col gap-1.5">
            <label className="text-xs font-semibold" style={{ color: '#374151' }}>
              Email address
            </label>
            <input
              type="email"
              value={email}
              onChange={e => setEmail(e.target.value)}
              placeholder="you@company.com"
              autoComplete="email"
              className="w-full px-4 py-2.5 rounded-lg text-sm outline-none transition-all"
              style={{
                border: '1px solid #D1D5DB',
                background: '#F9FAFB',
                color: '#111827',
              }}
              onFocus={e => (e.currentTarget.style.borderColor = '#4F46E5')}
              onBlur={e  => (e.currentTarget.style.borderColor = '#D1D5DB')}
            />
          </div>

          {/* Password */}
          <div className="flex flex-col gap-1.5">
            <label className="text-xs font-semibold" style={{ color: '#374151' }}>
              Password
            </label>
            <div className="relative">
              <input
                type={showPw ? 'text' : 'password'}
                value={password}
                onChange={e => setPassword(e.target.value)}
                placeholder="••••••••"
                autoComplete={mode === 'signin' ? 'current-password' : 'new-password'}
                className="w-full px-4 py-2.5 pr-10 rounded-lg text-sm outline-none transition-all"
                style={{
                  border: '1px solid #D1D5DB',
                  background: '#F9FAFB',
                  color: '#111827',
                }}
                onFocus={e => (e.currentTarget.style.borderColor = '#4F46E5')}
                onBlur={e  => (e.currentTarget.style.borderColor = '#D1D5DB')}
              />
              <button
                type="button"
                onClick={() => setShowPw(v => !v)}
                className="absolute right-3 top-1/2 -translate-y-1/2 border-0 bg-transparent cursor-pointer p-0"
                style={{ color: '#9CA3AF' }}
              >
                {showPw ? <EyeOff size={15} /> : <Eye size={15} />}
              </button>
            </div>
          </div>

          {/* Error / info */}
          {error && (
            <div
              className="flex items-center gap-2 px-3 py-2.5 rounded-lg text-xs"
              style={{ background: '#FEF2F2', color: '#DC2626', border: '1px solid #FECACA' }}
            >
              <AlertCircle size={13} strokeWidth={2} style={{ flexShrink: 0 }} />
              {error}
            </div>
          )}
          {info && (
            <div
              className="flex items-center gap-2 px-3 py-2.5 rounded-lg text-xs"
              style={{ background: '#F0FDF4', color: '#15803D', border: '1px solid #86EFAC' }}
            >
              {info}
            </div>
          )}

          {/* Submit */}
          <button
            type="submit"
            disabled={loading}
            className="flex items-center justify-center gap-2 w-full py-2.5 rounded-lg text-sm font-semibold text-white cursor-pointer border-0 transition-opacity"
            style={{
              background: loading ? '#A5B4FC' : 'linear-gradient(135deg, #4F46E5, #7C3AED)',
              opacity: loading ? 0.8 : 1,
            }}
          >
            {loading ? 'Please wait…' : mode === 'signin' ? 'Sign in' : 'Create account'}
            {!loading && <ArrowRight size={15} strokeWidth={2.5} />}
          </button>
        </form>

        {/* Toggle */}
        <p className="text-center text-xs mt-6" style={{ color: '#6B7280' }}>
          {mode === 'signin' ? "Don't have an account? " : 'Already have an account? '}
          <button
            onClick={toggle}
            className="font-semibold border-0 bg-transparent cursor-pointer p-0"
            style={{ color: '#4F46E5' }}
          >
            {mode === 'signin' ? 'Sign up' : 'Sign in'}
          </button>
        </p>
      </div>
    </div>
  );
}
