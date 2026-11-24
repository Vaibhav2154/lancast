import { ChangeEvent, FormEvent, useCallback, useEffect, useRef, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { Download, Plus, Upload, X } from "lucide-react";
import { AppShell } from "../components/AppShell";
import { StatusBadge } from "../components/StatusBadge";
import { useAuth } from "../hooks/useAuth";
import {
  AssessmentSummary,
  createAssessment,
  exportCapsule,
  importCapsule,
  listAssessments,
  transitionAssessment,
} from "../lib/api";

export function OrganizerDashboard() {
  const { activeTenantId } = useAuth();
  const navigate = useNavigate();
  const fileInputRef = useRef<HTMLInputElement | null>(null);

  const [assessments, setAssessments] = useState<AssessmentSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [search, setSearch] = useState("");
  const [busyId, setBusyId] = useState<string | null>(null);

  // Create modal
  const [showCreate, setShowCreate] = useState(false);
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [durationMinutes, setDurationMinutes] = useState(60);
  const [maxAttempts, setMaxAttempts] = useState(1);
  const [closesAt, setClosesAt] = useState("");
  const [creating, setCreating] = useState(false);
  const [importing, setImporting] = useState(false);

  const load = useCallback(async () => {
    if (!activeTenantId) {
      setAssessments([]);
      setLoading(false);
      return;
    }
    setLoading(true);
    setError(null);
    try {
      setAssessments(await listAssessments(activeTenantId));
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to load assessments");
    } finally {
      setLoading(false);
    }
  }, [activeTenantId]);

  useEffect(() => {
    void load();
  }, [load]);

  async function handleCreate(e: FormEvent) {
    e.preventDefault();
    if (!activeTenantId) return;
    setCreating(true);
    setError(null);
    try {
      const created = await createAssessment(activeTenantId, {
        title: title.trim(),
        description: description.trim(),
        config: {
          duration_minutes: Number(durationMinutes),
          max_attempts: Number(maxAttempts),
          closes_at: closesAt ? new Date(closesAt).toISOString() : null,
        },
      });
      setShowCreate(false);
      setTitle("");
      setDescription("");
      setClosesAt("");
      navigate(`/organizer/assessments/${created.id}`);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Could not create assessment");
    } finally {
      setCreating(false);
    }
  }

  async function handleTransition(
    assessmentId: string,
    action: "publish" | "start" | "close" | "archive"
  ) {
    if (!activeTenantId) return;
    setBusyId(assessmentId);
    setError(null);
    try {
      await transitionAssessment(activeTenantId, assessmentId, action);
      await load();
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : `Failed to ${action} assessment`);
    } finally {
      setBusyId(null);
    }
  }

  async function handleExport(assessmentId: string) {
    if (!activeTenantId) return;
    setBusyId(assessmentId);
    setError(null);
    try {
      const blob = await exportCapsule(activeTenantId, assessmentId);
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `capsule-${assessmentId}.zip`;
      a.click();
      URL.revokeObjectURL(url);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Capsule export failed");
    } finally {
      setBusyId(null);
    }
  }

  async function handleImportChange(e: ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    e.target.value = "";
    if (!file || !activeTenantId) return;
    setImporting(true);
    setError(null);
    try {
      const created = await importCapsule(activeTenantId, file);
      navigate(`/organizer/assessments/${created.id}`);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Capsule import failed");
    } finally {
      setImporting(false);
    }
  }

  const counts = {
    active: assessments.filter((a) => a.status === "active").length,
    published: assessments.filter((a) => a.status === "published").length,
    draft: assessments.filter((a) => a.status === "draft").length,
    closed: assessments.filter((a) => a.status === "closed").length,
  };

  const filtered = assessments.filter((a) =>
    a.title.toLowerCase().includes(search.trim().toLowerCase())
  );

  return (
    <AppShell
      kicker="Organizer Workspace"
      title="Department Assessments"
      actions={
        <>
          <input
            ref={fileInputRef}
            type="file"
            accept=".zip,application/zip"
            onChange={handleImportChange}
            className="hidden"
          />
          <button
            type="button"
            disabled={!activeTenantId || importing}
            onClick={() => fileInputRef.current?.click()}
            className="inline-flex cursor-pointer items-center gap-2 rounded-full border border-strong bg-surface px-4 py-2 text-xs font-bold text-ink transition hover:bg-elevated disabled:opacity-60"
          >
            <Upload className="h-3.5 w-3.5" />
            {importing ? "Importing..." : "Import Capsule (.zip)"}
          </button>
          <button
            type="button"
            disabled={!activeTenantId}
            onClick={() => setShowCreate(true)}
            className="inline-flex cursor-pointer items-center gap-2 rounded-full bg-accent px-5 py-2 text-xs font-bold text-on-accent shadow-sm transition hover:bg-accent-hover disabled:opacity-60"
          >
            <Plus className="h-4 w-4" /> New Assessment
          </button>
        </>
      }
    >
      <div className="space-y-6">
        {error && (
          <div className="rounded-xl bg-danger-soft px-4 py-3 text-sm font-semibold text-danger">
            {error}
          </div>
        )}

        {/* KPI Row */}
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <KpiCard label="Active Now" value={counts.active} sub="Accepting candidate attempts" />
          <KpiCard label="Published" value={counts.published} sub="Frozen & ready to start" />
          <KpiCard label="Drafts" value={counts.draft} sub="Editable configurations" />
          <KpiCard label="Closed" value={counts.closed} sub="Review & manual grading" />
        </div>

        {/* Assessments Table */}
        <div className="overflow-hidden rounded-2xl border border-subtle bg-surface shadow-xs">
          <div className="flex flex-col justify-between gap-3 border-b border-subtle px-6 py-4 sm:flex-row sm:items-center">
            <h2 className="text-base font-extrabold text-ink">
              All Assessments ({filtered.length})
            </h2>
            <input
              type="search"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Filter by title..."
              className="rounded-full border border-strong bg-input px-4 py-1.5 text-sm text-ink placeholder:text-ink-muted focus:border-accent focus:outline-none sm:w-64"
            />
          </div>

          {loading ? (
            <p className="p-6 text-sm text-ink-muted">Loading assessments...</p>
          ) : filtered.length === 0 ? (
            <div className="p-10 text-center text-sm text-ink-muted">
              No assessments found. Create one or import an Assessment Capsule (.zip).
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-left text-sm">
                <thead className="border-b border-subtle bg-elevated/70 text-xs font-bold uppercase tracking-wider text-ink-muted">
                  <tr>
                    <th className="px-6 py-3.5">Assessment</th>
                    <th className="px-6 py-3.5">Config</th>
                    <th className="px-6 py-3.5">Status</th>
                    <th className="px-6 py-3.5 text-right">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-subtle">
                  {filtered.map((a) => {
                    const busy = busyId === a.id;
                    return (
                      <tr key={a.id} className="transition hover:bg-elevated/40">
                        <td className="px-6 py-4">
                          <Link
                            to={`/organizer/assessments/${a.id}`}
                            className="font-bold text-ink hover:text-accent-text"
                          >
                            {a.title}
                          </Link>
                          <div className="mt-0.5 text-xs text-ink-muted">
                            v{a.version_number} {a.is_frozen ? "frozen" : "draft"}
                            {a.canonical_digest
                              ? ` • digest ${a.canonical_digest.slice(0, 10)}…`
                              : ""}
                          </div>
                        </td>
                        <td className="px-6 py-4 text-xs text-ink-secondary">
                          {a.config.duration_minutes} min • max {a.config.max_attempts} attempt
                          {a.config.max_attempts > 1 ? "s" : ""}
                        </td>
                        <td className="px-6 py-4">
                          <StatusBadge status={a.status} />
                        </td>
                        <td className="px-6 py-4">
                          <div className="flex flex-wrap justify-end gap-2 text-xs font-bold">
                            <Link
                              to={`/organizer/assessments/${a.id}`}
                              className="rounded-full border border-subtle bg-elevated px-3 py-1 text-ink hover:border-strong"
                            >
                              Open
                            </Link>
                            {a.status === "draft" && (
                              <button
                                type="button"
                                disabled={busy}
                                onClick={() => void handleTransition(a.id, "publish")}
                                className="cursor-pointer rounded-full bg-accent-soft px-3 py-1 text-accent-text hover:bg-accent hover:text-on-accent"
                              >
                                Publish
                              </button>
                            )}
                            {a.status === "published" && (
                              <button
                                type="button"
                                disabled={busy}
                                onClick={() => void handleTransition(a.id, "start")}
                                className="cursor-pointer rounded-full bg-accent-soft px-3 py-1 text-accent-text hover:bg-accent hover:text-on-accent"
                              >
                                Start
                              </button>
                            )}
                            {a.status === "active" && (
                              <button
                                type="button"
                                disabled={busy}
                                onClick={() => void handleTransition(a.id, "close")}
                                className="cursor-pointer rounded-full bg-warn-soft px-3 py-1 text-warn"
                              >
                                Close
                              </button>
                            )}
                            {a.status !== "draft" && (
                              <Link
                                to={`/organizer/assessments/${a.id}/results`}
                                className="rounded-full border border-subtle bg-surface px-3 py-1 text-ink hover:border-accent"
                              >
                                Results
                              </Link>
                            )}
                            <button
                              type="button"
                              disabled={busy}
                              onClick={() => void handleExport(a.id)}
                              title="Export Assessment Capsule (.zip)"
                              className="inline-flex cursor-pointer items-center gap-1 rounded-full border border-subtle bg-surface px-3 py-1 text-ink-secondary hover:text-ink"
                            >
                              <Download className="h-3 w-3" /> Capsule
                            </button>
                          </div>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>

      {/* Create Assessment Modal */}
      {showCreate && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4 backdrop-blur-xs">
          <div className="w-full max-w-lg rounded-2xl border border-subtle bg-surface p-6 shadow-2xl">
            <div className="mb-4 flex items-center justify-between border-b border-subtle pb-3">
              <div>
                <p className="text-xs font-bold uppercase tracking-wider text-accent-text">
                  New Assessment
                </p>
                <h2 className="text-lg font-extrabold text-ink">Create Draft Assessment</h2>
              </div>
              <button
                type="button"
                onClick={() => setShowCreate(false)}
                className="cursor-pointer rounded-full p-1 text-ink-muted hover:text-ink"
              >
                <X className="h-5 w-5" />
              </button>
            </div>

            <form onSubmit={handleCreate} className="space-y-4">
              <div>
                <label className="mb-1 block text-xs font-semibold text-ink-secondary">
                  Title
                </label>
                <input
                  type="text"
                  required
                  value={title}
                  onChange={(e) => setTitle(e.target.value)}
                  placeholder="DSA Midterm 2026"
                  className="w-full rounded-xl border border-strong bg-input px-3.5 py-2 text-sm text-ink"
                />
              </div>

              <div>
                <label className="mb-1 block text-xs font-semibold text-ink-secondary">
                  Description / Instructions
                </label>
                <textarea
                  rows={3}
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  placeholder="Instructions shown to enrolled candidates..."
                  className="w-full rounded-xl border border-strong bg-input px-3.5 py-2 text-sm text-ink"
                />
              </div>

              <div className="grid gap-4 sm:grid-cols-2">
                <div>
                  <label className="mb-1 block text-xs font-semibold text-ink-secondary">
                    Duration (minutes)
                  </label>
                  <input
                    type="number"
                    min={1}
                    max={1440}
                    required
                    value={durationMinutes}
                    onChange={(e) => setDurationMinutes(Number(e.target.value))}
                    className="w-full rounded-xl border border-strong bg-input px-3 py-2 text-sm text-ink"
                  />
                </div>
                <div>
                  <label className="mb-1 block text-xs font-semibold text-ink-secondary">
                    Max Attempts
                  </label>
                  <input
                    type="number"
                    min={1}
                    max={10}
                    required
                    value={maxAttempts}
                    onChange={(e) => setMaxAttempts(Number(e.target.value))}
                    className="w-full rounded-xl border border-strong bg-input px-3 py-2 text-sm text-ink"
                  />
                </div>
              </div>

              <div>
                <label className="mb-1 block text-xs font-semibold text-ink-secondary">
                  Window Closes At (optional)
                </label>
                <input
                  type="datetime-local"
                  value={closesAt}
                  onChange={(e) => setClosesAt(e.target.value)}
                  className="w-full rounded-xl border border-strong bg-input px-3 py-2 text-sm text-ink"
                />
              </div>

              <div className="flex justify-end gap-2.5 border-t border-subtle pt-4">
                <button
                  type="button"
                  onClick={() => setShowCreate(false)}
                  className="cursor-pointer rounded-full border border-strong bg-surface px-5 py-2 text-sm font-semibold text-ink"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={creating}
                  className="cursor-pointer rounded-full bg-accent px-6 py-2 text-sm font-bold text-on-accent hover:bg-accent-hover disabled:opacity-60"
                >
                  {creating ? "Creating..." : "Create Draft"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </AppShell>
  );
}

function KpiCard({ label, value, sub }: { label: string; value: number; sub: string }) {
  return (
    <div className="rounded-2xl border border-subtle bg-surface p-5 shadow-xs">
      <div className="text-xs font-bold text-ink-muted">{label}</div>
      <div className="mt-1.5 text-3xl font-extrabold tracking-tight text-ink">{value}</div>
      <div className="mt-1 text-xs font-medium text-accent-text">{sub}</div>
    </div>
  );
}
