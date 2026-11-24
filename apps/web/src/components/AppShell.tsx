import { ReactNode, useEffect, useState } from "react";
import { Link, NavLink, useNavigate } from "react-router-dom";
import {
  BookOpen,
  ClipboardList,
  LogOut,
  Moon,
  Shield,
  Sun,
  Users,
} from "lucide-react";
import { useAuth } from "../hooks/useAuth";
import { useTheme } from "../hooks/useTheme";
import { fetchReadiness, ReadinessInfo } from "../lib/api";
import { StatusBadge } from "./StatusBadge";

interface NavItem {
  to: string;
  label: string;
  icon: ReactNode;
  end?: boolean;
}

export function AppShell({
  title,
  kicker,
  actions,
  children,
}: {
  title: string;
  kicker?: string;
  actions?: ReactNode;
  children: ReactNode;
}) {
  const { me, activeTenantId, activeMembership, setActiveTenantId, signOut } = useAuth();
  const { theme, toggleTheme } = useTheme();
  const navigate = useNavigate();
  const [readiness, setReadiness] = useState<ReadinessInfo | null>(null);

  useEffect(() => {
    let active = true;
    fetchReadiness()
      .then((r) => active && setReadiness(r))
      .catch(() => {});
    return () => {
      active = false;
    };
  }, []);

  const navItems: NavItem[] = [];
  if (me?.user.is_platform_admin) {
    navItems.push({
      to: "/admin",
      label: "Platform & Tenants",
      icon: <Shield className="h-4 w-4" />,
    });
  }
  const hasOrgRole = me?.memberships.some(
    (m) => m.role === "organizer" || m.role === "tenant_admin"
  );
  if (hasOrgRole) {
    navItems.push({
      to: "/organizer",
      label: "Assessments",
      icon: <ClipboardList className="h-4 w-4" />,
      end: true,
    });
  }
  if (activeMembership?.role === "tenant_admin") {
    navItems.push({
      to: "/organizer/members",
      label: "Tenant Members",
      icon: <Users className="h-4 w-4" />,
    });
  }
  if (me?.memberships.some((m) => m.role === "candidate")) {
    navItems.push({
      to: "/candidate",
      label: "My Assessments",
      icon: <BookOpen className="h-4 w-4" />,
    });
  }

  async function handleSignOut() {
    await signOut();
    navigate("/");
  }

  return (
    <div className="min-h-screen flex flex-col bg-canvas text-ink transition-colors duration-150">
      {/* Top Bar */}
      <header className="sticky top-0 z-30 border-b border-subtle bg-surface/95 backdrop-blur-sm">
        <div className="mx-auto flex h-16 max-w-7xl items-center justify-between gap-4 px-4 sm:px-6">
          <div className="flex items-center gap-4">
            <Link to="/" className="text-xl font-extrabold tracking-tight text-ink">
              LANCAST<span className="text-accent">.</span>
            </Link>

            {me && me.memberships.length > 0 && (
              <div className="hidden items-center gap-2 sm:flex">
                <span className="text-xs font-semibold text-ink-muted">Tenant:</span>
                <select
                  aria-label="Active tenant"
                  value={activeTenantId ?? ""}
                  onChange={(e) => setActiveTenantId(e.target.value)}
                  className="rounded-full border border-subtle bg-elevated px-3 py-1 text-xs font-bold text-ink focus:border-accent focus:outline-none"
                >
                  {me.memberships.map((m) => (
                    <option key={m.tenant_id} value={m.tenant_id}>
                      {m.tenant_id.slice(0, 8)}… ({m.role})
                    </option>
                  ))}
                </select>
              </div>
            )}
          </div>

          <div className="flex items-center gap-2.5">
            {readiness && (
              <div className="hidden md:block">
                <StatusBadge
                  status={readiness.status}
                  label={`${readiness.deployment_profile === "central" ? "Central" : "Standalone"} • ${
                    readiness.status === "ready" ? "Ready" : "Degraded"
                  }`}
                />
              </div>
            )}

            <button
              type="button"
              onClick={toggleTheme}
              aria-label={`Switch to ${theme === "light" ? "dark" : "light"} mode`}
              className="inline-flex cursor-pointer items-center gap-1.5 rounded-full border border-subtle bg-elevated px-3 py-1.5 text-xs font-semibold text-ink transition hover:border-strong"
            >
              {theme === "light" ? (
                <>
                  <Moon className="h-3.5 w-3.5" />
                  <span className="hidden sm:inline">Dark</span>
                </>
              ) : (
                <>
                  <Sun className="h-3.5 w-3.5" />
                  <span className="hidden sm:inline">Light</span>
                </>
              )}
            </button>

            {me && (
              <div className="flex items-center gap-2 border-l border-subtle pl-2.5">
                <div className="hidden text-right leading-tight sm:block">
                  <div className="text-xs font-bold text-ink">{me.user.full_name}</div>
                  <div className="text-[11px] text-ink-muted">{me.user.email}</div>
                </div>
                <button
                  type="button"
                  onClick={handleSignOut}
                  className="inline-flex cursor-pointer items-center gap-1.5 rounded-full border border-subtle bg-surface px-3 py-1.5 text-xs font-semibold text-ink-secondary transition hover:border-danger/40 hover:text-danger"
                >
                  <LogOut className="h-3.5 w-3.5" />
                  <span className="hidden sm:inline">Sign Out</span>
                </button>
              </div>
            )}
          </div>
        </div>
      </header>

      <div className="mx-auto flex w-full max-w-7xl flex-1 flex-col gap-6 px-4 py-6 sm:px-6 lg:flex-row">
        {navItems.length > 0 && (
          <aside className="w-full shrink-0 lg:w-60">
            <nav className="flex flex-wrap gap-1.5 rounded-2xl border border-subtle bg-surface p-2.5 shadow-xs lg:flex-col">
              {navItems.map((item) => (
                <NavLink
                  key={item.to}
                  to={item.to}
                  end={item.end}
                  className={({ isActive }) =>
                    `flex items-center gap-2.5 rounded-xl px-3.5 py-2.5 text-sm font-semibold transition ${
                      isActive
                        ? "bg-accent-soft text-accent-text border border-accent-border"
                        : "text-ink-secondary hover:bg-elevated hover:text-ink border border-transparent"
                    }`
                  }
                >
                  {item.icon}
                  {item.label}
                </NavLink>
              ))}
            </nav>

            {me && (
              <div className="mt-4 hidden rounded-2xl border border-subtle bg-surface p-4 text-xs text-ink-muted lg:block">
                <div className="mb-1 font-bold text-ink">LAN-Only Session</div>
                <p className="leading-relaxed">
                  All assessments, scoring, and audit trails are enforced server-side.
                </p>
              </div>
            )}
          </aside>
        )}

        <main className="min-w-0 flex-1">
          <div className="mb-6 flex flex-col justify-between gap-4 sm:flex-row sm:items-end">
            <div>
              {kicker && (
                <p className="mb-1 text-xs font-bold uppercase tracking-wider text-accent-text">
                  {kicker}
                </p>
              )}
              <h1 className="text-2xl font-extrabold tracking-tight text-ink sm:text-3xl">
                {title}
              </h1>
            </div>
            {actions && <div className="flex flex-wrap items-center gap-2.5">{actions}</div>}
          </div>
          {children}
        </main>
      </div>
    </div>
  );
}
