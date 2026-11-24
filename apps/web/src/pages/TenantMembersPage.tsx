import { AppShell } from "../components/AppShell";
import { TenantMembersPanel } from "../components/TenantMembersPanel";
import { useAuth } from "../hooks/useAuth";

export function TenantMembersPage() {
  const { activeTenantId } = useAuth();

  return (
    <AppShell kicker="Tenant Administration" title="Tenant Members">
      {activeTenantId ? (
        <TenantMembersPanel tenantId={activeTenantId} />
      ) : (
        <div className="rounded-2xl border border-subtle bg-surface p-8 text-center text-sm text-ink-muted">
          No active tenant selected.
        </div>
      )}
    </AppShell>
  );
}
