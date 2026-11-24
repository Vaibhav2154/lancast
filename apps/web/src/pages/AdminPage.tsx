import { FormEvent, useCallback, useEffect, useState } from "react";
import { Building2, Plus } from "lucide-react";
import { AppShell } from "../components/AppShell";
import { TenantMembersPanel } from "../components/TenantMembersPanel";
import { createTenant, listTenants, Tenant } from "../lib/api";

export function AdminPage() {
  const [tenants, setTenants] = useState<Tenant[]>([]);
  const [selectedTenant, setSelectedTenant] = useState<Tenant | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [slug, setSlug] = useState("");
  const [name, setName] = useState("");
  const [creating, setCreating] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const items = await listTenants();
      setTenants(items);
      setSelectedTenant((prev) =>
        prev ? items.find((t) => t.id === prev.id) ?? items[0] ?? null : items[0] ?? null
      );
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to load tenants");
    } finally {
      setLoading(false);
    }
  }, []);

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
    <AppShell kicker="Platform Administration" title="Tenants & Memberships">
      <div className="space-y-6">
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
