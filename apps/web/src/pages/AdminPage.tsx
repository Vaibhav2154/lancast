import { FormEvent, useCallback, useEffect, useState } from "react";
import { Activity, Building2, Cpu, Plus, RefreshCw } from "lucide-react";
import { AppShell } from "../components/AppShell";
import { StatusBadge } from "../components/StatusBadge";
import { TenantMembersPanel } from "../components/TenantMembersPanel";
import {
  createTenant,
  getAdminInfrastructure,
  getAdminTelemetry,
  InfrastructureStatus,
  listTenants,
  TelemetryOverview,
  Tenant,
} from "../lib/api";

export function AdminPage() {
  const [tenants, setTenants] = useState<Tenant[]>([]);
  const [selectedTenant, setSelectedTenant] = useState<Tenant | null>(null);
  const [infra, setInfra] = useState<InfrastructureStatus | null>(null);
  const [telemetry, setTelemetry] = useState<TelemetryOverview | null>(null);
  const [infraLoading, setInfraLoading] = useState(true);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [slug, setSlug] = useState("");
  const [name, setName] = useState("");
  const [creating, setCreating] = useState(false);

  const loadInfra = useCallback(async () => {
    setInfraLoading(true);
    try {
      const [infraData, telemetryData] = await Promise.all([
        getAdminInfrastructure(),
        getAdminTelemetry().catch(() => null),
      ]);
      setInfra(infraData);
      setTelemetry(telemetryData);
    } catch {
      // Non-fatal: tenant administration remains usable even if telemetry fails.
    } finally {
      setInfraLoading(false);
    }
  }, []);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [items] = await Promise.all([listTenants(), loadInfra()]);
      setTenants(items);
      setSelectedTenant((prev) =>
        prev ? items.find((t) => t.id === prev.id) ?? items[0] ?? null : items[0] ?? null
      );
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to load tenants");
    } finally {
      setLoading(false);
    }
  }, [loadInfra]);

  useEffect(() => {
    void load();
  }, [load]);

  async function handleCreateTenant(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setCreating(true);
    try {
      const created = await createTenant(slug.trim().toLowerCase(), name.trim());
      setSlug("");
      setName("");
      await load();
      setSelectedTenant(created);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Could not create tenant");
    } finally {
      setCreating(false);
    }
  }

  return (
    <AppShell kicker="Platform Administration" title="Tenants & Infrastructure">
      <div className="space-y-6">
        <div className="rounded-2xl border border-subtle bg-surface p-6 shadow-xs">
          <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
            <div className="flex items-center gap-2.5">
              <Cpu className="h-5 w-5 text-accent-text" />
              <div>
                <h2 className="text-base font-extrabold text-ink">
                  Infrastructure & Execution Workers
                </h2>
                <p className="text-xs text-ink-muted">
                  Profile:{" "}
                  <span className="font-mono font-bold text-ink">
                    {infra?.deployment_profile ?? "..."}
                  </span>{" "}
                  • Environment:{" "}
                  <span className="font-mono text-ink">{infra?.environment ?? "..."}</span>
                </p>
              </div>
            </div>

            <button
              type="button"
              disabled={infraLoading}
              onClick={() => void loadInfra()}
              className="inline-flex cursor-pointer items-center gap-1.5 rounded-full border border-subtle bg-elevated px-3.5 py-1.5 text-xs font-bold text-ink hover:border-strong disabled:opacity-60"
            >
              <RefreshCw className={`h-3.5 w-3.5 ${infraLoading ? "animate-spin" : ""}`} />
              Refresh
            </button>
          </div>

          {infra && (
            <div className="space-y-4">
              <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-5">
                <div className="rounded-xl border border-subtle bg-elevated/50 px-4 py-3">
                  <div className="mb-1 text-[11px] font-bold uppercase tracking-wider text-ink-muted">
                    PostgreSQL
                  </div>
                  <StatusBadge status={infra.dependencies.postgres} />
                </div>
                <div className="rounded-xl border border-subtle bg-elevated/50 px-4 py-3">
                  <div className="mb-1 text-[11px] font-bold uppercase tracking-wider text-ink-muted">
                    Redis Queue
                  </div>
                  <StatusBadge status={infra.dependencies.redis} />
                </div>
                <div className="rounded-xl border border-subtle bg-elevated/50 px-4 py-3">
                  <div className="mb-1 text-[11px] font-bold uppercase tracking-wider text-ink-muted">
                    Judge0 Sandbox
                  </div>
                  <StatusBadge status={infra.dependencies.judge0} />
                </div>
                <div className="rounded-xl border border-subtle bg-elevated/50 px-4 py-3">
                  <div className="mb-1 text-[11px] font-bold uppercase tracking-wider text-ink-muted">
                    Queued Jobs
                  </div>
                  <div className="text-lg font-extrabold text-ink">
                    {infra.queue_depth ?? "—"}
                  </div>
                </div>
                <div className="rounded-xl border border-subtle bg-elevated/50 px-4 py-3">
                  <div className="mb-1 text-[11px] font-bold uppercase tracking-wider text-ink-muted">
                    Dead-Letter Jobs
                  </div>
                  <div className="text-lg font-extrabold text-ink">
                    {infra.dead_letter_depth ?? "—"}
                  </div>
                </div>
              </div>

              {infra.workers.length === 0 ? (
                <p className="rounded-xl border border-subtle bg-elevated/40 px-4 py-3 text-xs text-ink-muted">
                  No execution worker heartbeats recorded yet. Start{" "}
                  <code className="font-mono text-ink">dispatcher</code> to register workers.
                </p>
              ) : (
                <div className="overflow-x-auto rounded-xl border border-subtle">
                  <table className="w-full text-left text-xs">
                    <thead className="border-b border-subtle bg-elevated/70 font-bold uppercase tracking-wider text-ink-muted">
                      <tr>
                        <th className="px-4 py-2.5">Worker ID</th>
                        <th className="px-4 py-2.5">Host</th>
                        <th className="px-4 py-2.5">Mode</th>
                        <th className="px-4 py-2.5">Status</th>
                        <th className="px-4 py-2.5">Judge0</th>
                        <th className="px-4 py-2.5">Completed / Failed</th>
                        <th className="px-4 py-2.5">Last Heartbeat</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-subtle">
                      {infra.workers.map((w) => (
                        <tr key={w.worker_id} className="hover:bg-elevated/30">
                          <td className="px-4 py-2.5 font-mono font-bold text-ink">
                            {w.worker_id}
                          </td>
                          <td className="px-4 py-2.5 font-mono text-ink-secondary">
                            {w.hostname}
                          </td>
                          <td className="px-4 py-2.5 text-ink-secondary">{w.deployment_mode}</td>
                          <td className="px-4 py-2.5">
                            <StatusBadge status={w.status} />
                          </td>
                          <td className="px-4 py-2.5">
                            <StatusBadge status={w.judge0_ok ? "ok" : "unreachable"} />
                          </td>
                          <td className="px-4 py-2.5 font-semibold text-ink">
                            {w.jobs_completed} / {w.jobs_failed}
                          </td>
                          <td className="px-4 py-2.5 text-ink-muted">
                            {new Date(w.last_heartbeat_at).toLocaleTimeString()}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}

              {telemetry && (
                <div className="space-y-3 border-t border-subtle pt-4">
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <div className="flex items-center gap-2">
                      <Activity className="h-4 w-4 text-accent-text" />
                      <h3 className="text-xs font-extrabold uppercase tracking-wider text-ink">
                        Host Telemetry &amp; Workload Latency
                      </h3>
                      <StatusBadge
                        status={telemetry.telemetry_state}
                        label={
                          telemetry.safe_fallback_active
                            ? `${telemetry.telemetry_state} — Safe Fallback`
                            : "Healthy"
                        }
                      />
                    </div>
                    <span className="text-[11px] text-ink-muted">
                      Stale window: {telemetry.stale_threshold_seconds}s • Operator Grafana:{" "}
                      <code className="font-mono text-ink">http://127.0.0.1:3000</code>
                    </span>
                  </div>

                  {telemetry.machines.length === 0 ? (
                    <p className="rounded-xl border border-subtle bg-elevated/40 px-4 py-2.5 text-xs text-ink-muted">
                      No telemetry samples received yet — orchestration stays in safe fallback mode
                      until fresh samples arrive.
                    </p>
                  ) : (
                    <div className="grid gap-3 md:grid-cols-2">
                      {telemetry.machines.map((m) => (
                        <div
                          key={m.machine_id}
                          className="rounded-xl border border-subtle bg-elevated/40 px-4 py-3 text-xs"
                        >
                          <div className="mb-2 flex items-center justify-between gap-2">
                            <span className="font-mono font-bold text-ink">
                              {m.machine_id}{" "}
                              <span className="font-normal text-ink-muted">({m.role})</span>
                            </span>
                            <div className="flex items-center gap-2">
                              <span className="text-[11px] text-ink-muted">{m.age_seconds}s ago</span>
                              <StatusBadge status={m.stale ? "stale" : m.healthy ? "healthy" : "degraded"} />
                            </div>
                          </div>
                          <div className="grid grid-cols-4 gap-2 text-[11px]">
                            <div>
                              <span className="block text-ink-muted">CPU</span>
                              <span className="font-bold text-ink">{m.cpu_percent.toFixed(1)}%</span>
                            </div>
                            <div>
                              <span className="block text-ink-muted">RAM</span>
                              <span className="font-bold text-ink">{m.memory_percent.toFixed(1)}%</span>
                            </div>
                            <div>
                              <span className="block text-ink-muted">Disk</span>
                              <span className="font-bold text-ink">{m.disk_percent.toFixed(1)}%</span>
                            </div>
                            <div>
                              <span className="block text-ink-muted">Net RX/TX</span>
                              <span className="font-bold text-ink">
                                {m.network_rx_kbps.toFixed(0)}/{m.network_tx_kbps.toFixed(0)} KB/s
                              </span>
                            </div>
                          </div>
                        </div>
                      ))}
                    </div>
                  )}

                  {Object.keys(telemetry.workload_latencies).length > 0 && (
                    <div className="flex flex-wrap gap-2">
                      {Object.entries(telemetry.workload_latencies).map(([wclass, stats]) => (
                        <div
                          key={wclass}
                          className="rounded-lg border border-subtle bg-elevated/50 px-3 py-1.5 text-[11px]"
                        >
                          <span className="font-mono font-bold text-accent-text">{wclass}</span>{" "}
                          <span className="text-ink-muted">({stats.count})</span>:{" "}
                          <span className="font-semibold text-ink">
                            P50 {stats.p50_ms}ms • P95 {stats.p95_ms}ms • P99 {stats.p99_ms}ms
                          </span>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              )}
            </div>
          )}
        </div>

        <div className="rounded-2xl border border-subtle bg-surface p-6 shadow-xs">
          <h2 className="mb-1 text-base font-extrabold text-ink">Create Tenant</h2>
          <p className="mb-4 text-xs text-ink-muted">
            Register an independent department, lab, or campus club. Slug must be lowercase
            alphanumeric with hyphens.
          </p>

          <form onSubmit={handleCreateTenant} className="grid gap-3 sm:grid-cols-3">
            <input
              type="text"
              required
              pattern="^[a-z0-9][a-z0-9-]{1,63}$"
              value={slug}
              onChange={(e) => setSlug(e.target.value)}
              placeholder="cse-dept"
              className="rounded-xl border border-strong bg-input px-3.5 py-2 text-sm text-ink"
            />
            <input
              type="text"
              required
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="CSE Department"
              className="rounded-xl border border-strong bg-input px-3.5 py-2 text-sm text-ink"
            />
            <button
              type="submit"
              disabled={creating}
              className="inline-flex cursor-pointer items-center justify-center gap-2 rounded-full bg-accent px-5 py-2 text-sm font-bold text-on-accent hover:bg-accent-hover disabled:opacity-60"
            >
              <Plus className="h-4 w-4" />
              {creating ? "Creating..." : "Create Tenant"}
            </button>
          </form>

          {error && (
            <p className="mt-3 rounded-xl bg-danger-soft px-3.5 py-2 text-xs font-semibold text-danger">
              {error}
            </p>
          )}
        </div>

        <div className="grid gap-6 lg:grid-cols-12">
          <div className="rounded-2xl border border-subtle bg-surface p-5 shadow-xs lg:col-span-4">
            <h3 className="mb-3 text-sm font-extrabold text-ink">
              Registered Tenants ({tenants.length})
            </h3>
            {loading ? (
              <p className="text-sm text-ink-muted">Loading...</p>
            ) : tenants.length === 0 ? (
              <p className="text-sm text-ink-muted">No tenants created yet.</p>
            ) : (
              <div className="space-y-2">
                {tenants.map((t) => {
                  const active = selectedTenant?.id === t.id;
                  return (
                    <button
                      key={t.id}
                      type="button"
                      onClick={() => setSelectedTenant(t)}
                      className={`flex w-full cursor-pointer items-center justify-between rounded-xl border px-3.5 py-3 text-left transition ${
                        active
                          ? "border-accent-border bg-accent-soft text-accent-text"
                          : "border-subtle bg-elevated/50 text-ink hover:border-strong"
                      }`}
                    >
                      <div>
                        <div className="text-sm font-bold">{t.name}</div>
                        <div className="text-xs opacity-75">/{t.slug}</div>
                      </div>
                      <Building2 className="h-4 w-4 shrink-0" />
                    </button>
                  );
                })}
              </div>
            )}
          </div>

          <div className="lg:col-span-8">
            {selectedTenant ? (
              <TenantMembersPanel
                tenantId={selectedTenant.id}
                tenantLabel={selectedTenant.name}
              />
            ) : (
              <div className="rounded-2xl border border-subtle bg-surface p-8 text-center text-sm text-ink-muted">
                Create or select a tenant to manage its memberships.
              </div>
            )}
          </div>
        </div>
      </div>
    </AppShell>
  );
}
