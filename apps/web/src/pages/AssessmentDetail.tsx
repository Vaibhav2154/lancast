import { FormEvent, useCallback, useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { ArrowLeft, Download, Lock, Plus, Trash2 } from "lucide-react";
import { AppShell } from "../components/AppShell";
import { QuestionEditor, QuestionPayload } from "../components/QuestionEditor";
import { StatusBadge } from "../components/StatusBadge";
import { useAuth } from "../hooks/useAuth";
import {
  addQuestion,
  AssessmentDetail as AssessmentDetailModel,
  deleteQuestion,
  enrollCandidates,
  Enrollment,
  exportCapsule,
  getAssessmentDetail,
  listEnrollments,
  OrganizerQuestion,
  previewAssessment,
  PreviewResponse,
  transitionAssessment,
  updateAssessment,
  updateQuestion,
} from "../lib/api";

type Tab = "questions" | "enrollments" | "preview" | "settings";

export function AssessmentDetail() {
  const { assessmentId } = useParams<{ assessmentId: string }>();
  const { activeTenantId } = useAuth();

  const [detail, setDetail] = useState<AssessmentDetailModel | null>(null);
  const [enrollments, setEnrollments] = useState<Enrollment[]>([]);
  const [preview, setPreview] = useState<PreviewResponse | null>(null);
  const [tab, setTab] = useState<Tab>("questions");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  // Question editor modal
  const [editorOpen, setEditorOpen] = useState(false);
  const [editingQuestion, setEditingQuestion] = useState<OrganizerQuestion | null>(null);
  const [savingQuestion, setSavingQuestion] = useState(false);

  // Enrollment input
  const [emailInput, setEmailInput] = useState("");
  const [enrolling, setEnrolling] = useState(false);

  // Settings form
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [durationMinutes, setDurationMinutes] = useState(60);
  const [maxAttempts, setMaxAttempts] = useState(1);

  const load = useCallback(async () => {
    if (!activeTenantId || !assessmentId) return;
    setLoading(true);
    setError(null);
    try {
      const [d, enr] = await Promise.all([
        getAssessmentDetail(activeTenantId, assessmentId),
        listEnrollments(activeTenantId, assessmentId),
      ]);
      setDetail(d);
      setEnrollments(enr);
      setTitle(d.title);
      setDescription(d.description);
      setDurationMinutes(d.config.duration_minutes);
      setMaxAttempts(d.config.max_attempts);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to load assessment");
    } finally {
      setLoading(false);
    }
  }, [activeTenantId, assessmentId]);

  useEffect(() => {
    void load();
  }, [load]);

  async function loadPreview() {
    if (!activeTenantId || !assessmentId) return;
    setError(null);
    try {
      setPreview(await previewAssessment(activeTenantId, assessmentId));
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to load preview");
    }
  }

  async function handleTransition(action: "publish" | "start" | "close" | "archive") {
    if (!activeTenantId || !assessmentId) return;
    setBusy(true);
    setError(null);
    setNotice(null);
    try {
      await transitionAssessment(activeTenantId, assessmentId, action);
      setNotice(`Assessment ${action}ed successfully.`);
      await load();
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : `Failed to ${action}`);
    } finally {
      setBusy(false);
    }
  }

  async function handleSaveQuestion(payload: QuestionPayload) {
    if (!activeTenantId || !assessmentId) return;
    setSavingQuestion(true);
    try {
      if (editingQuestion) {
        await updateQuestion(activeTenantId, assessmentId, editingQuestion.id, {
          prompt: payload.prompt,
          hidden_eval: payload.hidden_eval,
          max_score: payload.max_score,
        });
      } else {
        await addQuestion(activeTenantId, assessmentId, payload);
      }
      setEditorOpen(false);
      setEditingQuestion(null);
      await load();
    } finally {
      setSavingQuestion(false);
    }
  }

  async function handleDeleteQuestion(qid: string) {
    if (!activeTenantId || !assessmentId) return;
    setError(null);
    try {
      await deleteQuestion(activeTenantId, assessmentId, qid);
      await load();
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Could not delete question");
    }
  }

  async function handleEnroll(e: FormEvent) {
    e.preventDefault();
    if (!activeTenantId || !assessmentId) return;
    const emails = emailInput
      .split(/[\s,;]+/)
      .map((s) => s.trim())
      .filter(Boolean);
    if (emails.length === 0) return;

    setEnrolling(true);
    setError(null);
    setNotice(null);
    try {
      const res = await enrollCandidates(activeTenantId, assessmentId, emails);
      setEmailInput("");
      setNotice(`Enrolled ${res.added.length} new candidate(s).`);
      await load();
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Enrollment failed");
    } finally {
      setEnrolling(false);
    }
  }

  async function handleSaveSettings(e: FormEvent) {
    e.preventDefault();
    if (!activeTenantId || !assessmentId || !detail) return;
    setBusy(true);
    setError(null);
    setNotice(null);
    try {
      await updateAssessment(activeTenantId, assessmentId, {
        title: title.trim(),
        description: description.trim(),
        config: {
          duration_minutes: Number(durationMinutes),
          max_attempts: Number(maxAttempts),
          closes_at: detail.config.closes_at,
        },
      });
      setNotice("Settings updated.");
      await load();
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Could not update settings");
    } finally {
      setBusy(false);
    }
  }

  async function handleExport() {
    if (!activeTenantId || !assessmentId) return;
    try {
      const blob = await exportCapsule(activeTenantId, assessmentId);
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `capsule-${assessmentId}.zip`;
      a.click();
      URL.revokeObjectURL(url);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Export failed");
    }
  }

  const editable = detail ? !detail.is_frozen && detail.status === "draft" : false;

  return (
    <AppShell
      kicker="Assessment Workspace"
      title={detail?.title ?? "Loading Assessment..."}
      actions={
        detail && (
          <>
            <Link
              to="/organizer"
              className="inline-flex items-center gap-1.5 rounded-full border border-subtle bg-surface px-4 py-2 text-xs font-bold text-ink hover:bg-elevated"
            >
              <ArrowLeft className="h-3.5 w-3.5" /> Back
            </Link>
            <button
              type="button"
              onClick={() => void handleExport()}
              className="inline-flex cursor-pointer items-center gap-1.5 rounded-full border border-subtle bg-surface px-4 py-2 text-xs font-bold text-ink hover:bg-elevated"
            >
              <Download className="h-3.5 w-3.5" /> Export Capsule
            </button>
            {detail.status === "draft" && (
              <button
                type="button"
                disabled={busy}
                onClick={() => void handleTransition("publish")}
                className="cursor-pointer rounded-full bg-accent px-5 py-2 text-xs font-bold text-on-accent hover:bg-accent-hover disabled:opacity-60"
              >
                Publish &amp; Freeze
              </button>
            )}
            {detail.status === "published" && (
              <button
                type="button"
                disabled={busy}
                onClick={() => void handleTransition("start")}
                className="cursor-pointer rounded-full bg-accent px-5 py-2 text-xs font-bold text-on-accent hover:bg-accent-hover disabled:opacity-60"
              >
                Start Assessment
              </button>
            )}
            {detail.status === "active" && (
              <button
                type="button"
                disabled={busy}
                onClick={() => void handleTransition("close")}
                className="cursor-pointer rounded-full bg-warn-soft px-5 py-2 text-xs font-bold text-warn"
              >
                Close Assessment
              </button>
            )}
            {detail.status === "closed" && (
              <button
                type="button"
                disabled={busy}
                onClick={() => void handleTransition("archive")}
                className="cursor-pointer rounded-full border border-strong bg-elevated px-5 py-2 text-xs font-bold text-ink"
              >
                Archive
              </button>
            )}
            {detail.status !== "draft" && (
              <Link
                to={`/organizer/assessments/${detail.id}/results`}
                className="rounded-full border border-accent-border bg-accent-soft px-5 py-2 text-xs font-bold text-accent-text"
              >
                View Results
              </Link>
            )}
          </>
        )
      }
    >
      {loading || !detail ? (
        <div className="rounded-2xl border border-subtle bg-surface p-8 text-sm text-ink-muted">
          {error ?? "Loading assessment details..."}
        </div>
      ) : (
        <div className="space-y-6">
          {error && (
            <div className="rounded-xl bg-danger-soft px-4 py-3 text-sm font-semibold text-danger">
              {error}
            </div>
          )}
          {notice && (
            <div className="rounded-xl border border-accent-border bg-accent-soft px-4 py-3 text-sm font-semibold text-accent-text">
              {notice}
            </div>
          )}

          {/* Status & Digest Strip */}
          <div className="flex flex-wrap items-center justify-between gap-4 rounded-2xl border border-subtle bg-surface px-6 py-4 shadow-xs">
            <div className="flex flex-wrap items-center gap-3">
              <StatusBadge status={detail.status} />
              <span className="text-xs font-semibold text-ink-secondary">
                Version {detail.version_number} • {detail.config.duration_minutes} min • max{" "}
                {detail.config.max_attempts} attempt(s)
              </span>
            </div>
            {detail.is_frozen && (
              <div className="inline-flex items-center gap-2 rounded-full border border-subtle bg-elevated px-3.5 py-1 text-xs font-mono text-ink-secondary">
                <Lock className="h-3.5 w-3.5 text-accent-text" />
                SHA-256: {detail.canonical_digest?.slice(0, 16)}…
              </div>
            )}
          </div>

          {/* Tabs */}
          <div className="flex flex-wrap gap-2 border-b border-subtle pb-3">
            {(
              [
                ["questions", `Questions (${detail.questions.length})`],
                ["enrollments", `Enrollments (${enrollments.length})`],
                ["preview", "Candidate Preview"],
                ["settings", "Settings"],
              ] as [Tab, string][]
            ).map(([key, label]) => (
              <button
                key={key}
                type="button"
                onClick={() => {
                  setTab(key);
                  if (key === "preview") void loadPreview();
                }}
                className={`cursor-pointer rounded-full px-4 py-1.5 text-xs font-bold transition ${
                  tab === key
                    ? "bg-accent text-on-accent"
                    : "border border-subtle bg-surface text-ink-secondary hover:text-ink"
                }`}
              >
                {label}
              </button>
            ))}
          </div>

          {tab === "questions" && (
            <div className="space-y-4">
              {!editable && (
                <div className="flex items-center gap-2 rounded-xl border border-subtle bg-elevated px-4 py-3 text-xs font-semibold text-ink-secondary">
                  <Lock className="h-4 w-4 text-accent-text" />
                  Published versions are frozen and cryptographically hashed; questions cannot be
                  modified.
                </div>
              )}

              {editable && (
                <div className="flex justify-end">
                  <button
                    type="button"
                    onClick={() => {
                      setEditingQuestion(null);
                      setEditorOpen(true);
                    }}
                    className="inline-flex cursor-pointer items-center gap-2 rounded-full bg-accent px-5 py-2 text-xs font-bold text-on-accent hover:bg-accent-hover"
                  >
                    <Plus className="h-4 w-4" /> Add Question
                  </button>
                </div>
              )}

              {detail.questions.length === 0 ? (
                <div className="rounded-2xl border border-subtle bg-surface p-10 text-center text-sm text-ink-muted">
                  No questions added yet. Add at least one question before publishing.
                </div>
              ) : (
                <div className="space-y-3">
                  {detail.questions.map((q) => (
                    <div
                      key={q.id}
                      className="flex flex-col justify-between gap-4 rounded-2xl border border-subtle bg-surface p-5 shadow-xs sm:flex-row sm:items-start"
                    >
                      <div className="space-y-1.5">
                        <div className="flex flex-wrap items-center gap-2">
                          <span className="text-xs font-extrabold text-accent-text">
                            Q{q.position}
                          </span>
                          <span className="rounded-full bg-elevated px-2.5 py-0.5 text-[11px] font-bold uppercase text-ink-secondary">
                            {q.question_type}
                          </span>
                          <span className="text-xs font-semibold text-ink-muted">
                            {q.max_score} pts
                          </span>
                        </div>
                        <p className="text-sm font-semibold text-ink">
                          {String(q.prompt.text ?? "")}
                        </p>
                      </div>

                      {editable && (
                        <div className="flex shrink-0 items-center gap-2">
                          <button
                            type="button"
                            onClick={() => {
                              setEditingQuestion(q);
                              setEditorOpen(true);
                            }}
                            className="cursor-pointer rounded-full border border-subtle bg-elevated px-3.5 py-1 text-xs font-bold text-ink hover:border-strong"
                          >
                            Edit
                          </button>
                          <button
                            type="button"
                            onClick={() => void handleDeleteQuestion(q.id)}
                            className="cursor-pointer rounded-full p-1.5 text-ink-muted hover:text-danger"
                          >
                            <Trash2 className="h-4 w-4" />
                          </button>
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

          {tab === "enrollments" && (
            <div className="space-y-6">
              <div className="rounded-2xl border border-subtle bg-surface p-6 shadow-xs">
                <h3 className="mb-1 text-sm font-extrabold text-ink">Enroll Candidates</h3>
                <p className="mb-3 text-xs text-ink-muted">
                  Enter candidate emails (separated by commas or new lines). Every email must belong
                  to this tenant with the candidate role.
                </p>
                <form onSubmit={handleEnroll} className="space-y-3">
                  <textarea
                    rows={3}
                    value={emailInput}
                    onChange={(e) => setEmailInput(e.target.value)}
                    placeholder="alice@campus.edu, bob@campus.edu"
                    className="w-full rounded-xl border border-strong bg-input px-3.5 py-2.5 text-sm text-ink"
                  />
                  <button
                    type="submit"
                    disabled={enrolling}
                    className="cursor-pointer rounded-full bg-accent px-5 py-2 text-xs font-bold text-on-accent hover:bg-accent-hover disabled:opacity-60"
                  >
                    {enrolling ? "Enrolling..." : "Enroll Candidates"}
                  </button>
                </form>
              </div>

              <div className="overflow-hidden rounded-2xl border border-subtle bg-surface shadow-xs">
                <div className="border-b border-subtle px-6 py-3.5 text-sm font-extrabold text-ink">
                  Enrolled Candidates ({enrollments.length})
                </div>
                {enrollments.length === 0 ? (
                  <p className="p-6 text-sm text-ink-muted">No candidates enrolled yet.</p>
                ) : (
                  <ul className="divide-y divide-subtle">
                    {enrollments.map((enr) => (
                      <li
                        key={enr.email}
                        className="flex items-center justify-between px-6 py-3 text-sm"
                      >
                        <span className="font-semibold text-ink">{enr.full_name}</span>
                        <span className="text-ink-secondary">{enr.email}</span>
                      </li>
                    ))}
                  </ul>
                )}
              </div>
            </div>
          )}

          {tab === "preview" && (
            <div className="space-y-4">
              {!preview ? (
                <div className="rounded-2xl border border-subtle bg-surface p-6 text-sm text-ink-muted">
                  Loading candidate-safe preview...
                </div>
              ) : (
                preview.questions.map((q) => (
                  <div
                    key={q.id}
                    className="rounded-2xl border border-subtle bg-surface p-5 shadow-xs"
                  >
                    <div className="mb-2 flex items-center justify-between">
                      <span className="text-xs font-bold uppercase text-accent-text">
                        Question {q.position} • {q.question_type}
                      </span>
                      <span className="rounded-full bg-elevated px-3 py-0.5 text-xs font-bold text-ink">
                        {q.max_score} pts
                      </span>
                    </div>
                    <p className="text-sm font-semibold text-ink">{String(q.prompt.text ?? "")}</p>
                    {Array.isArray(q.prompt.options) && (
                      <ul className="mt-3 space-y-1.5 text-sm text-ink-secondary">
                        {(q.prompt.options as { id: string; text: string }[]).map((o) => (
                          <li
                            key={o.id}
                            className="rounded-lg border border-subtle bg-elevated/50 px-3 py-2"
                          >
                            <strong className="mr-2 font-mono text-xs">{o.id}.</strong>
                            {o.text}
                          </li>
                        ))}
                      </ul>
                    )}
                  </div>
                ))
              )}
            </div>
          )}

          {tab === "settings" && (
            <form
              onSubmit={handleSaveSettings}
              className="space-y-4 rounded-2xl border border-subtle bg-surface p-6 shadow-xs"
            >
              <div>
                <label className="mb-1 block text-xs font-semibold text-ink-secondary">
                  Title
                </label>
                <input
                  type="text"
                  disabled={!editable}
                  required
                  value={title}
                  onChange={(e) => setTitle(e.target.value)}
                  className="w-full rounded-xl border border-strong bg-input px-3.5 py-2 text-sm text-ink disabled:opacity-60"
                />
              </div>
              <div>
                <label className="mb-1 block text-xs font-semibold text-ink-secondary">
                  Description
                </label>
                <textarea
                  rows={3}
                  disabled={!editable}
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  className="w-full rounded-xl border border-strong bg-input px-3.5 py-2 text-sm text-ink disabled:opacity-60"
                />
              </div>
              <div className="grid gap-4 sm:grid-cols-2">
                <div>
                  <label className="mb-1 block text-xs font-semibold text-ink-secondary">
                    Duration (minutes)
                  </label>
                  <input
                    type="number"
                    disabled={!editable}
                    min={1}
                    max={1440}
                    value={durationMinutes}
                    onChange={(e) => setDurationMinutes(Number(e.target.value))}
                    className="w-full rounded-xl border border-strong bg-input px-3 py-2 text-sm text-ink disabled:opacity-60"
                  />
                </div>
                <div>
                  <label className="mb-1 block text-xs font-semibold text-ink-secondary">
                    Max Attempts
                  </label>
                  <input
                    type="number"
                    disabled={!editable}
                    min={1}
                    max={10}
                    value={maxAttempts}
                    onChange={(e) => setMaxAttempts(Number(e.target.value))}
                    className="w-full rounded-xl border border-strong bg-input px-3 py-2 text-sm text-ink disabled:opacity-60"
                  />
                </div>
              </div>
              {editable && (
                <button
                  type="submit"
                  disabled={busy}
                  className="cursor-pointer rounded-full bg-accent px-6 py-2 text-xs font-bold text-on-accent hover:bg-accent-hover disabled:opacity-60"
                >
                  {busy ? "Saving..." : "Save Settings"}
                </button>
              )}
            </form>
          )}
        </div>
      )}

      {editorOpen && (
        <QuestionEditor
          initial={editingQuestion}
          saving={savingQuestion}
          onSave={handleSaveQuestion}
          onCancel={() => {
            setEditorOpen(false);
            setEditingQuestion(null);
          }}
        />
      )}
    </AppShell>
  );
}
