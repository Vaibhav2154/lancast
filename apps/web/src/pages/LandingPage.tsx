import { FormEvent, useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { ArrowRight, BookOpen, ClipboardList, Moon, Shield, Sun } from "lucide-react";
import { primaryPortalPath, useAuth } from "../hooks/useAuth";
import { useTheme } from "../hooks/useTheme";
import { fetchHealth, fetchReadiness, HealthInfo, ReadinessInfo } from "../lib/api";

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
  const { me, signIn, registerFirstAdmin, signOut } = useAuth();
  const navigate = useNavigate();

  const [health, setHealth] = useState<HealthInfo | null>(null);
  const [readiness, setReadiness] = useState<ReadinessInfo | null>(null);

  const [mode, setMode] = useState<"login" | "bootstrap">("login");
  const [fullName, setFullName] = useState("");
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
    return () => {
      active = false;
    };
  }, []);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setAuthError(null);
    setSubmitting(true);
    try {
      const profile =
        mode === "login"
          ? await signIn(email, password)
          : await registerFirstAdmin(email, fullName, password);
      setPassword("");
      const dest = primaryPortalPath(profile);
      if (dest !== "/") {
        navigate(dest);
      }
    } catch (err: unknown) {
      setAuthError(err instanceof Error ? err.message : "Authentication failed");
    } finally {
      setSubmitting(false);
    }
  }

  const profileLabel = health
    ? `${health.deployment_profile === "central" ? "Central" : "Standalone"} LAN`
    : "Campus LAN";
  const isReady = readiness?.status === "ready";

  const hasOrganizer = Boolean(
    me?.memberships.some((m) => m.role === "organizer" || m.role === "tenant_admin")
  );
  const hasCandidate = Boolean(me?.memberships.some((m) => m.role === "candidate"));

  return (
    <div className="min-h-screen flex flex-col bg-canvas text-ink transition-colors duration-200">
      {/* Unified Neutral + Emerald Hero */}
      <section
        className="relative overflow-hidden border-b border-subtle text-on-brand"
        style={{
          background:
            "linear-gradient(135deg, var(--brand-gradient-start) 0%, var(--brand-gradient-end) 100%)",
        }}
      >
        <div
          aria-hidden="true"
          className="pointer-events-none absolute -top-24 left-1/4 h-[420px] w-[620px] rounded-full bg-emerald-500/10 blur-3xl dark:bg-emerald-500/12"
        />

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
          <Link to="/" className="text-2xl font-extrabold tracking-tight text-ink">
            LANCAST<span className="text-accent">.</span>
          </Link>

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
                  <Moon className="h-3.5 w-3.5" />
                  Dark
                </>
              ) : (
                <>
                  <Sun className="h-3.5 w-3.5" />
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
              <Link
                to={me ? primaryPortalPath(me) : "/#portal-signin"}
                className="inline-flex items-center justify-center gap-2 rounded-full bg-accent px-8 py-3.5 text-sm font-bold text-on-accent shadow-lg shadow-emerald-950/15 transition hover:bg-accent-hover"
              >
                {me ? "Open Workspace" : "Explore Workspace"}
                <ArrowRight className="h-4 w-4" />
              </Link>
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

                  <div className="mb-5 space-y-2">
                    {me.user.is_platform_admin && (
                      <Link
                        to="/admin"
                        className="flex items-center justify-between rounded-xl border border-subtle bg-elevated px-4 py-3 text-sm font-bold text-ink transition hover:border-accent"
                      >
                        <span className="flex items-center gap-2.5">
                          <Shield className="h-4 w-4 text-accent-text" /> Platform &amp; Tenants
                        </span>
                        <ArrowRight className="h-4 w-4 text-ink-muted" />
                      </Link>
                    )}
                    {hasOrganizer && (
                      <Link
                        to="/organizer"
                        className="flex items-center justify-between rounded-xl border border-subtle bg-elevated px-4 py-3 text-sm font-bold text-ink transition hover:border-accent"
                      >
                        <span className="flex items-center gap-2.5">
                          <ClipboardList className="h-4 w-4 text-accent-text" /> Organizer Portal
                        </span>
                        <ArrowRight className="h-4 w-4 text-ink-muted" />
                      </Link>
                    )}
                    {hasCandidate && (
                      <Link
                        to="/candidate"
                        className="flex items-center justify-between rounded-xl border border-subtle bg-elevated px-4 py-3 text-sm font-bold text-ink transition hover:border-accent"
                      >
                        <span className="flex items-center gap-2.5">
                          <BookOpen className="h-4 w-4 text-accent-text" /> Candidate Assessments
                        </span>
                        <ArrowRight className="h-4 w-4 text-ink-muted" />
                      </Link>
                    )}
                    {!me.user.is_platform_admin && me.memberships.length === 0 && (
                      <p className="rounded-xl bg-elevated p-3 text-xs text-ink-secondary">
                        You do not belong to any tenant yet. Ask an administrator to enroll you.
                      </p>
                    )}
                  </div>

                  <button
                    type="button"
                    onClick={() => void signOut()}
                    className="w-full cursor-pointer rounded-full border border-strong bg-surface px-5 py-3 text-sm font-bold text-ink transition hover:bg-elevated"
                  >
                    Sign Out
                  </button>
                </div>
              ) : (
                <form onSubmit={handleSubmit} className="space-y-4">
                  <div className="flex items-center justify-between gap-2">
                    <div>
                      <p className="mb-1 text-xs font-bold uppercase tracking-wider text-accent-text">
                        {mode === "login" ? "Local Authentication" : "First-Run Setup"}
                      </p>
                      <h2 className="text-xl font-extrabold tracking-tight text-ink">
                        {mode === "login" ? "Sign in to LANCAST" : "Bootstrap Admin"}
                      </h2>
                    </div>

                    <button
                      type="button"
                      onClick={() => {
                        setAuthError(null);
                        setMode((m) => (m === "login" ? "bootstrap" : "login"));
                      }}
                      className="cursor-pointer rounded-full border border-subtle bg-elevated px-3 py-1 text-[11px] font-bold text-ink-secondary transition hover:border-strong hover:text-ink"
                    >
                      {mode === "login" ? "First-Run Setup" : "Back to Sign In"}
                    </button>
                  </div>

                  {mode === "bootstrap" && (
                    <div>
                      <label
                        htmlFor="fullName"
                        className="mb-1.5 block text-xs font-semibold text-ink-secondary"
                      >
                        Full Name
                      </label>
                      <input
                        id="fullName"
                        type="text"
                        required
                        value={fullName}
                        onChange={(e) => setFullName(e.target.value)}
                        placeholder="Platform Administrator"
                        className="w-full rounded-xl border border-strong bg-input px-3.5 py-2.5 text-sm text-ink placeholder:text-ink-muted focus:border-accent focus:outline-none focus:ring-2 focus:ring-accent/20"
                      />
                    </div>
                  )}

                  <div>
                    <label
                      htmlFor="email"
                      className="mb-1.5 block text-xs font-semibold text-ink-secondary"
                    >
                      Campus Email
                    </label>
                    <input
                      id="email"
                      type="email"
                      required
                      value={email}
                      onChange={(e) => setEmail(e.target.value)}
                      placeholder="organizer@cse.campus.edu"
                      className="w-full rounded-xl border border-strong bg-input px-3.5 py-2.5 text-sm text-ink placeholder:text-ink-muted focus:border-accent focus:outline-none focus:ring-2 focus:ring-accent/20"
                    />
                  </div>

                  <div>
                    <label
                      htmlFor="password"
                      className="mb-1.5 block text-xs font-semibold text-ink-secondary"
                    >
                      Password {mode === "bootstrap" && "(min 10 chars)"}
                    </label>
                    <input
                      id="password"
                      type="password"
                      required
                      minLength={mode === "bootstrap" ? 10 : 1}
                      value={password}
                      onChange={(e) => setPassword(e.target.value)}
                      placeholder="••••••••••••"
                      className="w-full rounded-xl border border-strong bg-input px-3.5 py-2.5 text-sm text-ink placeholder:text-ink-muted focus:border-accent focus:outline-none focus:ring-2 focus:ring-accent/20"
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
                    {submitting
                      ? "Authenticating..."
                      : mode === "login"
                        ? "Sign In to Portal"
                        : "Create Platform Admin"}
                  </button>

                  <p className="pt-1 text-center text-xs text-ink-muted">
                    {mode === "login"
                      ? "Protected by local Argon2 sessions • LAN-only access"
                      : "Only allowed when zero users exist in the database"}
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
    <span
      className={`inline-flex items-center gap-2 rounded-full border px-4 py-1.5 text-xs font-bold ${styles}`}
    >
      <span className={`h-2 w-2 rounded-full ${dot}`} />
      {label}: {pending ? "Checking" : ok ? "Healthy" : "Unreachable"}
    </span>
  );
}
