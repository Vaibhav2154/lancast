import { FormEvent, useCallback, useEffect, useState } from "react";
import { UserPlus } from "lucide-react";
import { addMember, listMembers, Member, TenantRole } from "../lib/api";

export function TenantMembersPanel({
  tenantId,
  tenantLabel,
}: {
  tenantId: string;
  tenantLabel?: string;
}) {
  const [members, setMembers] = useState<Member[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [email, setEmail] = useState("");
  const [role, setRole] = useState<TenantRole>("candidate");
  const [fullName, setFullName] = useState("");
  const [password, setPassword] = useState("");
  const [saving, setSaving] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      setMembers(await listMembers(tenantId));
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to load members");
    } finally {
      setLoading(false);
    }
  }, [tenantId]);

  useEffect(() => {
    void load();
  }, [load]);

  async function handleAdd(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setSaving(true);
    try {
      await addMember(tenantId, {
        email: email.trim(),
        role,
        full_name: fullName.trim() || undefined,
        password: password || undefined,
      });
      setEmail("");
      setFullName("");
      setPassword("");
      await load();
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Could not add member");
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="space-y-6">
      <div className="rounded-2xl border border-subtle bg-surface p-6 shadow-xs">
        <h2 className="mb-1 text-base font-extrabold text-ink">
          Add Member {tenantLabel ? `— ${tenantLabel}` : ""}
        </h2>
        <p className="mb-4 text-xs text-ink-muted">
          If the email does not exist yet, supply Full Name and Password (min 10 chars) to create
          the account simultaneously.
        </p>

        <form onSubmit={handleAdd} className="grid gap-3 sm:grid-cols-2 lg:grid-cols-5">
          <input
            type="email"
            required
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder="user@campus.edu"
            className="rounded-xl border border-strong bg-input px-3 py-2 text-sm text-ink"
          />
          <select
            value={role}
            onChange={(e) => setRole(e.target.value as TenantRole)}
            className="rounded-xl border border-strong bg-input px-3 py-2 text-sm text-ink"
          >
            <option value="candidate">Candidate</option>
            <option value="organizer">Organizer</option>
            <option value="tenant_admin">Tenant Admin</option>
          </select>
          <input
            type="text"
            value={fullName}
            onChange={(e) => setFullName(e.target.value)}
            placeholder="Full Name (if new user)"
            className="rounded-xl border border-strong bg-input px-3 py-2 text-sm text-ink"
          />
          <input
            type="password"
            minLength={password ? 10 : undefined}
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            placeholder="Password (if new user)"
            className="rounded-xl border border-strong bg-input px-3 py-2 text-sm text-ink"
          />
          <button
            type="submit"
            disabled={saving}
            className="inline-flex cursor-pointer items-center justify-center gap-2 rounded-full bg-accent px-4 py-2 text-sm font-bold text-on-accent hover:bg-accent-hover disabled:opacity-60"
          >
            <UserPlus className="h-4 w-4" />
            {saving ? "Adding..." : "Add Member"}
          </button>
        </form>

        {error && (
          <p className="mt-3 rounded-xl bg-danger-soft px-3.5 py-2 text-xs font-semibold text-danger">
            {error}
          </p>
        )}
      </div>

      <div className="overflow-hidden rounded-2xl border border-subtle bg-surface shadow-xs">
        <div className="border-b border-subtle px-6 py-4">
          <h3 className="text-sm font-extrabold text-ink">
            Memberships ({members.length})
          </h3>
        </div>
        {loading ? (
          <p className="p-6 text-sm text-ink-muted">Loading members...</p>
        ) : members.length === 0 ? (
          <p className="p-6 text-sm text-ink-muted">No members in this tenant yet.</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead className="border-b border-subtle bg-elevated/70 text-xs font-bold uppercase tracking-wider text-ink-muted">
                <tr>
                  <th className="px-6 py-3">Name</th>
                  <th className="px-6 py-3">Email</th>
                  <th className="px-6 py-3">Role</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-subtle">
                {members.map((m) => (
                  <tr key={m.user_id}>
                    <td className="px-6 py-3.5 font-semibold text-ink">{m.full_name}</td>
                    <td className="px-6 py-3.5 text-ink-secondary">{m.email}</td>
                    <td className="px-6 py-3.5">
                      <span className="rounded-full border border-subtle bg-elevated px-3 py-0.5 text-xs font-bold text-ink">
                        {m.role}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
