import { FormEvent, useEffect, useState } from "react";
import { useTheme } from "../hooks/useTheme";
import {
  fetchHealth,
  fetchMe,
  fetchReadiness,
  getStoredToken,
  HealthInfo,
  login,
  logout,
  MeResponse,
  ReadinessInfo,
  setStoredToken,
} from "../lib/api";

const TENANTS = [
  { name: "CSE Dept", style: "font-extrabold text-ink-secondary" },
  { name: "PLACEMENT CELL", style: "font-medium tracking-[0.2em] text-sm text-ink-muted" },
  { name: "ECE Lab", style: "font-bold text-ink-secondary" },
  { name: "ACM Chapter", style: "font-extrabold text-ink-secondary" },
  { name: "Robotics Club", style: "font-normal text-ink-muted" },
  { name: "AI & Systems", style: "font-bold text-ink-secondary" },
];

const FEATURES = [
  {
    num: "01",
    title: "Multi-Tenant Isolation",
    body: "Strict server-side RBAC per department or club with frozen version SHA-256 digests and audited cross-tenant denials.",
  },
  {
    num: "02",
    title: "Isolated Judge0 Pool",
    body: "Untrusted candidate code executes out-of-process behind a bounded Redis queue with strict CPU, memory, and network limits.",
  },
  {
    num: "03",
    title: "Durable Autosave",
    body: "Server-authoritative exam deadlines with monotonic sequence autosaves and replay-resistant idempotent submissions.",
  },
];

export function LandingPage() {
  const { theme, toggleTheme } = useTheme();

  const [health, setHealth] = useState<HealthInfo | null>(null);
  const [readiness, setReadiness] = useState<ReadinessInfo | null>(null);
  const [me, setMe] = useState<MeResponse | null>(null);

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [authError, setAuthError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    let active = true;
    fetchHealth()
      .then((h) => active && setHealth(h))
      .catch(() => {});
    fetchReadiness()
      .then((r) => active && setReadiness(r))
      .catch(() => {});

    const existing = getStoredToken();
    if (existing) {
      fetchMe(existing)
        .then((profile) => active && setMe(profile))
        .catch(() => setStoredToken(null));
    }
    return () => {
      active = false;
    };
  }, []);

  async function handleLogin(e: FormEvent) {
    e.preventDefault();
    setAuthError(null);
    setSubmitting(true);
    try {
      const res = await login(email.trim(), password);
      setStoredToken(res.access_token);
      const profile = await fetchMe(res.access_token);
      setMe(profile);
      setPassword("");
    } catch (err: unknown) {
      setAuthError(err instanceof Error ? err.message : "Sign in failed");
    } finally {
      setSubmitting(false);
    }
  }

  async function handleLogout() {
    const token = getStoredToken();
    if (token) await logout(token);
    setStoredToken(null);
    setMe(null);
  }

  const profileLabel = health
    ? `${health.deployment_profile === "central" ? "Central" : "Standalone"} LAN`
    : "Campus LAN";
  const isReady = readiness?.status === "ready";

  return (
    <div className="min-h-screen flex flex-col bg-canvas text-ink transition-colors duration-200">
      {/* Unified Neutral + Emerald Hero (light & dark twin) */}
      <section
        className="relative overflow-hidden border-b border-subtle text-on-brand"
        style={{
          background:
            "linear-gradient(135deg, var(--brand-gradient-start) 0%, var(--brand-gradient-end) 100%)",
        }}
      >
        {/* Subtle emerald ambient glow in both light and dark mode */}
        <div
          aria-hidden="true"
          className="pointer-events-none absolute -top-24 left-1/4 h-[420px] w-[620px] rounded-full bg-emerald-500/10 blur-3xl dark:bg-emerald-500/12"
        />
        {/* Subtle geometric desk/laptop vector art (adapts via currentColor) */}
        <svg
          aria-hidden="true"
          className="pointer-events-none absolute inset-0 h-full w-full text-ink opacity-[0.06] dark:text-white dark:opacity-[0.11]"
          viewBox="0 0 1440 580"
          preserveAspectRatio="xMidYMid slice"
        >
          <circle cx="810" cy="120" r="145" fill="none" stroke="currentColor" strokeWidth="26" />
          <circle cx="810" cy="120" r="102" fill="none" stroke="currentColor" strokeWidth="4" />
          <g transform="translate(1060,-30) rotate(24)">
            <rect x="0" y="0" width="420" height="290" rx="22" fill="none" stroke="currentColor" strokeWidth="10" />
            <rect x="28" y="34" width="364" height="190" rx="10" fill="none" stroke="currentColor" strokeWidth="4" />
            <g fill="currentColor" opacity="0.55">
              <rect x="44" y="54" width="44" height="26" rx="5" />
              <rect x="98" y="54" width="44" height="26" rx="5" />
              <rect x="152" y="54" width="44" height="26" rx="5" />
              <rect x="206" y="54" width="44" height="26" rx="5" />
              <rect x="260" y="54" width="44" height="26" rx="5" />
              <rect x="314" y="54" width="60" height="26" rx="5" />
              <rect x="44" y="92" width="64" height="26" rx="5" />
              <rect x="118" y="92" width="44" height="26" rx="5" />
              <rect x="172" y="92" width="44" height="26" rx="5" />
              <rect x="226" y="92" width="44" height="26" rx="5" />
              <rect x="280" y="92" width="94" height="26" rx="5" />
              <rect x="44" y="130" width="84" height="26" rx="5" />
              <rect x="138" y="130" width="140" height="26" rx="5" />
              <rect x="288" y="130" width="86" height="26" rx="5" />
            </g>
          </g>
          <g transform="translate(-40,340) rotate(-18)">
            <rect x="0" y="0" width="290" height="320" rx="14" fill="none" stroke="currentColor" strokeWidth="8" />
            <line x1="36" y1="60" x2="245" y2="60" stroke="currentColor" strokeWidth="4" />
            <line x1="36" y1="95" x2="245" y2="95" stroke="currentColor" strokeWidth="4" />
            <line x1="36" y1="130" x2="215" y2="130" stroke="currentColor" strokeWidth="4" />
          </g>
        </svg>

        {/* Top Navigation */}
        <header className="relative z-10 mx-auto flex max-w-6xl items-center justify-between px-6 py-6 sm:px-8">
          <a href="#" className="text-2xl font-extrabold tracking-tight text-ink">
            LANCAST<span className="text-accent">.</span>
          </a>

          <nav className="hidden items-center gap-8 text-sm font-medium text-ink-secondary md:flex">
            <a href="#why-lancast" className="transition hover:text-ink">
              Overview
            </a>
            <a href="#architecture" className="transition hover:text-ink">
              Architecture
            </a>
            <a href="/api/docs" className="transition hover:text-ink">
              API Docs
            </a>
          </nav>

          <div className="flex items-center gap-3">
            <span className="hidden items-center gap-2 rounded-full border border-subtle bg-surface/80 px-3.5 py-1.5 text-xs font-semibold text-ink shadow-xs backdrop-blur-xs sm:inline-flex">
              <span
                className={`h-2 w-2 rounded-full ${
                  isReady ? "bg-emerald-500" : readiness ? "bg-amber-500" : "bg-ink-muted"
                }`}
              />
              {profileLabel} • {isReady ? "Ready" : readiness ? "Degraded" : "Checking"}
            </span>

            <button
              type="button"
              onClick={toggleTheme}
              aria-label={`Switch to ${theme === "light" ? "dark" : "light"} mode`}
              className="inline-flex cursor-pointer items-center gap-2 rounded-full border border-strong bg-surface/85 px-3.5 py-1.5 text-xs font-semibold text-ink shadow-xs backdrop-blur-xs transition hover:bg-elevated"
            >
              {theme === "light" ? (
                <>
                  <svg className="h-3.5 w-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z" />
                  </svg>
                  Dark
                </>
              ) : (
                <>
                  <svg className="h-3.5 w-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <circle cx="12" cy="12" r="4" />
                    <path d="M12 2v2M12 20v2M4.93 4.93l1.41 1.41M17.66 17.66l1.41 1.41M2 12h2M20 12h2M6.34 17.66l-1.41 1.41M19.07 4.93l-1.41 1.41" />
                  </svg>
                  Light
                </>
              )}
            </button>
          </div>
        </header>

        {/* Hero Main Content */}
        <div className="relative z-10 mx-auto grid max-w-6xl items-center gap-12 px-6 pt-6 pb-16 sm:px-8 lg:grid-cols-12 lg:pb-20">
          <div className="lg:col-span-7">
            <p className="mb-3.5 text-sm font-bold text-accent-text">
              Self-Hosted Campus Assessment Platform
            </p>
            <h1 className="mb-5 text-4xl font-extrabold leading-[1.08] tracking-tight text-ink sm:text-5xl lg:text-[54px]">
              Reliable Exams
              <br />
              Built for Campus LAN
            </h1>
            <p className="mb-8 max-w-lg text-base leading-relaxed text-ink-secondary">
              Multi-tenant MCQ, descriptive, file-upload, and sandboxed programming assessments with
              zero client Internet dependency.
            </p>
            <div className="flex flex-wrap items-center gap-3.5">
              <a
                href="#portal-signin"
                className="inline-flex items-center justify-center rounded-full bg-accent px-8 py-3.5 text-sm font-bold text-on-accent shadow-lg shadow-emerald-950/15 transition hover:bg-accent-hover"
              >
                Explore Workspace
              </a>
              <a
                href="/api/docs"
                className="inline-flex items-center justify-center rounded-full border border-strong bg-surface px-7 py-3.5 text-sm font-semibold text-ink transition hover:bg-elevated"
              >
                OpenAPI Docs
              </a>
            </div>
          </div>

          {/* Floating Portal Sign-In Card */}
          <div id="portal-signin" className="lg:col-span-5">
            <div className="rounded-2xl border border-subtle border-t-4 border-t-accent bg-surface p-7 text-ink shadow-xl shadow-emerald-950/10 dark:border-white/12 dark:border-t-accent dark:bg-surface/95 dark:shadow-black/40 sm:p-8">
              {me ? (
                <div>
                  <p className="mb-1 text-xs font-bold uppercase tracking-wider text-accent-text">
                    Signed In
                  </p>
                  <h2 className="mb-1 text-xl font-extrabold tracking-tight">{me.user.full_name}</h2>
                  <p className="mb-5 text-sm text-ink-muted">{me.user.email}</p>

                  <div className="mb-6 rounded-xl border border-subtle bg-elevated p-4 text-sm">
                    <div className="mb-2 flex items-center justify-between">
                      <span className="text-ink-secondary">Platform Admin</span>
                      <span className="font-bold text-ink">
                        {me.user.is_platform_admin ? "Yes" : "No"}
                      </span>
                    </div>
                    <div className="flex items-center justify-between">
                      <span className="text-ink-secondary">Tenant Memberships</span>
                      <span className="font-bold text-brand-text">{me.memberships.length}</span>
                    </div>
                  </div>

                  <button
                    type="button"
                    onClick={handleLogout}
                    className="w-full cursor-pointer rounded-full border border-strong bg-surface px-5 py-3 text-sm font-bold text-ink transition hover:bg-elevated"
                  >
                    Sign Out
                  </button>
                </div>
              ) : (
                <form onSubmit={handleLogin} className="space-y-4">
                  <div>
                    <p className="mb-1 text-xs font-bold uppercase tracking-wider text-accent-text">
                      Local Authentication
                    </p>
                    <h2 className="text-xl font-extrabold tracking-tight text-ink">
                      Sign in to LANCAST
                    </h2>
                  </div>

                  <div>
                    <label htmlFor="email" className="mb-1.5 block text-xs font-semibold text-ink-secondary">
                      Campus Email
                    </label>
                    <input
                      id="email"
                      type="email"
                      required
                      value={email}
                      onChange={(e) => setEmail(e.target.value)}
                      placeholder="organizer@cse.campus.edu"
                      className="w-full rounded-xl border border-strong bg-input px-3.5 py-2.5 text-sm text-ink placeholder:text-ink-muted focus:border-brand focus:outline-none focus:ring-2 focus:ring-brand/20"
                    />
                  </div>

                  <div>
                    <label htmlFor="password" className="mb-1.5 block text-xs font-semibold text-ink-secondary">
                      Password
                    </label>
                    <input
                      id="password"
                      type="password"
                      required
                      value={password}
                      onChange={(e) => setPassword(e.target.value)}
                      placeholder="••••••••••••"
                      className="w-full rounded-xl border border-strong bg-input px-3.5 py-2.5 text-sm text-ink placeholder:text-ink-muted focus:border-brand focus:outline-none focus:ring-2 focus:ring-brand/20"
                    />
                  </div>

                  {authError && (
                    <p className="rounded-lg bg-danger-soft px-3.5 py-2 text-xs font-semibold text-danger">
                      {authError}
                    </p>
                  )}

                  <button
                    type="submit"
                    disabled={submitting}
                    className="w-full cursor-pointer rounded-full bg-accent px-5 py-3 text-sm font-bold text-on-accent shadow-md transition hover:bg-accent-hover disabled:cursor-not-allowed disabled:opacity-60"
                  >
                    {submitting ? "Signing in..." : "Sign In to Portal"}
                  </button>

                  <p className="pt-1 text-center text-xs text-ink-muted">
                    Protected by local Argon2 sessions • LAN-only access
                  </p>
                </form>
              )}
            </div>
          </div>
        </div>
      </section>

      {/* Tenant / Department Strip */}
      <section className="border-b border-subtle bg-surface py-7">
        <div className="mx-auto flex max-w-6xl flex-wrap items-center justify-center gap-x-12 gap-y-4 px-6 sm:px-8">
          {TENANTS.map((tenant) => (
            <span key={tenant.name} className={`text-base sm:text-lg ${tenant.style}`}>
              {tenant.name}
            </span>
          ))}
        </div>
      </section>

      {/* Why LANCAST Overview */}
      <section id="why-lancast" className="mx-auto w-full max-w-6xl px-6 py-14 sm:px-8">
        <div className="grid items-start gap-10 lg:grid-cols-12">
          <div className="lg:col-span-4">
            <p className="mb-2.5 text-xs font-bold uppercase tracking-wider text-accent-text">
              Why LANCAST
            </p>
            <h2 className="mb-3 text-3xl font-extrabold leading-tight tracking-tight text-ink">
              Adaptive resource &amp; security orchestration
            </h2>
            <p className="text-sm leading-relaxed text-ink-secondary">
              Run concurrent department exams on local hardware with bounded queues, isolated code
              execution, and hash-linked audit trails.
            </p>
          </div>

          <div className="grid gap-5 sm:grid-cols-3 lg:col-span-8">
            {FEATURES.map((item) => (
              <div
                key={item.num}
                className="rounded-2xl border border-subtle bg-surface p-6 shadow-sm shadow-emerald-950/5 transition hover:-translate-y-0.5 hover:border-accent/50"
              >
                <div className="mb-4 inline-flex h-10 w-10 items-center justify-center rounded-xl border border-accent-border bg-accent-soft text-sm font-extrabold text-accent-text">
                  {item.num}
                </div>
                <h3 className="mb-2 text-base font-bold text-ink">{item.title}</h3>
                <p className="text-sm leading-relaxed text-ink-secondary">{item.body}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Live Infrastructure Readiness Strip */}
      <section id="architecture" className="mx-auto w-full max-w-6xl px-6 pb-14 sm:px-8">
        <div className="flex flex-col justify-between gap-6 rounded-2xl border border-subtle bg-surface p-6 sm:flex-row sm:items-center sm:px-8">
          <div>
            <p className="mb-1 text-xs font-bold uppercase tracking-wider text-accent-text">
              Live Gateway Telemetry
            </p>
            <h3 className="text-lg font-extrabold text-ink">
              {health ? `${health.service} v${health.version}` : "Connecting to LANCAST Gateway"}
            </h3>
            <p className="text-sm text-ink-secondary">
              Traefik → React SPA (nginx) + FastAPI → Local PostgreSQL &amp; Redis
            </p>
          </div>

          <div className="flex flex-wrap gap-3">
            <StatusBadge
              label="PostgreSQL"
              ok={readiness?.dependencies.postgres === "ok"}
              pending={!readiness}
            />
            <StatusBadge
              label="Redis Queue"
              ok={readiness?.dependencies.redis === "ok"}
              pending={!readiness}
            />
          </div>
        </div>
      </section>

      <footer className="mt-auto border-t border-subtle bg-surface py-6">
        <div className="mx-auto flex max-w-6xl flex-col items-center justify-between gap-2 px-6 text-xs text-ink-muted sm:flex-row sm:px-8">
          <span>
            <strong className="font-bold text-ink">LANCAST.</strong> Self-Hosted Campus Assessment
            Framework
          </span>
          <span>Zero external client dependencies • MIT License</span>
        </div>
      </footer>
    </div>
  );
}

function StatusBadge({ label, ok, pending }: { label: string; ok: boolean; pending: boolean }) {
  const styles = pending
    ? "bg-elevated text-ink-muted border-subtle"
    : ok
      ? "bg-accent-soft text-accent-text border-accent-border"
      : "bg-danger-soft text-danger border-danger/30";
  const dot = pending ? "bg-ink-muted" : ok ? "bg-accent" : "bg-danger";

  return (
    <span className={`inline-flex items-center gap-2 rounded-full border px-4 py-1.5 text-xs font-bold ${styles}`}>
      <span className={`h-2 w-2 rounded-full ${dot}`} />
      {label}: {pending ? "Checking" : ok ? "Healthy" : "Unreachable"}
    </span>
  );
}
