import { useState, type FormEvent } from "react";
import { Link, useNavigate } from "react-router-dom";

import { GlassPanel } from "../components/GlassPanel";
import BlurText from "../components/reactbits/BlurText";
import { useAuth } from "../auth/AuthContext";

export default function LoginPage() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      await login(email, password);
      navigate("/chat", { replace: true });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Login failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="grid min-h-full place-items-center p-6">
      <GlassPanel strong className="w-full max-w-[400px] p-8">
        <form onSubmit={handleSubmit}>
          <div className="mb-6 font-bold tracking-wide">
            <span className="text-accent-2">◆</span> <span className="brand-gradient">MemoryRAG</span>
          </div>
          <BlurText
            text="Welcome back"
            className="text-[1.7rem] font-bold tracking-tight leading-tight"
            animateBy="words"
            delay={120}
          />
          <p className="text-fg-muted mt-1 mb-2">Log in to your MemoryRAG workspace.</p>

          <label className="field-label" htmlFor="email">
            Email
          </label>
          <input
            id="email"
            type="email"
            autoComplete="username"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
          />

          <label className="field-label" htmlFor="password">
            Password
          </label>
          <input
            id="password"
            type="password"
            autoComplete="current-password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
          />

          {error && (
            <div className="mt-4 rounded-xl border border-[rgba(251,113,133,0.4)] bg-[rgba(251,113,133,0.12)] px-3 py-2.5 text-sm text-[#fecaca]">
              {error}
            </div>
          )}

          <button type="submit" className="primary mt-6 w-full" disabled={busy}>
            {busy ? "Logging in…" : "Log in"}
          </button>

          <p className="text-fg-muted mt-5 text-center">
            No account? <Link to="/register">Create one</Link>
          </p>
        </form>
      </GlassPanel>
    </div>
  );
}
