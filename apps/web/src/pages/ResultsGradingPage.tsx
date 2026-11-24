import { Fragment, useCallback, useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { ArrowLeft, Check } from "lucide-react";
import { AppShell } from "../components/AppShell";
import { StatusBadge } from "../components/StatusBadge";
import { useAuth } from "../hooks/useAuth";
import {
  AssessmentDetail,
  getAssessmentDetail,
  getAssessmentResults,
  gradeSubmissionQuestion,
  ResultRow,
} from "../lib/api";

export function ResultsGradingPage() {
  const { assessmentId } = useParams<{ assessmentId: string }>();
  const { activeTenantId } = useAuth();

  const [detail, setDetail] = useState<AssessmentDetail | null>(null);
  const [rows, setRows] = useState<ResultRow[]>([]);
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [gradeDrafts, setGradeDrafts] = useState<Record<string, string>>({});
  const [loading, setLoading] = useState(true);
  const [savingKey, setSavingKey] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    if (!activeTenantId || !assessmentId) return;
    setLoading(true);
    setError(null);
    try {
      const [d, r] = await Promise.all([
        getAssessmentDetail(activeTenantId, assessmentId),
        getAssessmentResults(activeTenantId, assessmentId),
      ]);
      setDetail(d);
      setRows(r);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to load results");
    } finally {
      setLoading(false);
    }
  }, [activeTenantId, assessmentId]);

  useEffect(() => {
    void load();
  }, [load]);

  async function handleSaveGrade(submissionId: string, questionId: string) {
    if (!activeTenantId) return;
    const key = `${submissionId}:${questionId}`;
    const raw = gradeDrafts[key];
    const score = Number(raw);
    if (Number.isNaN(score) || score < 0) {
      setError("Enter a valid non-negative score.");
      return;
    }
    setSavingKey(key);
    setError(null);
    try {
      await gradeSubmissionQuestion(activeTenantId, submissionId, questionId, score);
      await load();
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to save grade");
    } finally {
      setSavingKey(null);
    }
  }

  return (
    <AppShell
      kicker="Results & Grading"
      title={detail ? `${detail.title} — Results` : "Assessment Results"}
      actions={
        <Link
          to={assessmentId ? `/organizer/assessments/${assessmentId}` : "/organizer"}
          className="inline-flex items-center gap-1.5 rounded-full border border-subtle bg-surface px-4 py-2 text-xs font-bold text-ink hover:bg-elevated"
        >
          <ArrowLeft className="h-3.5 w-3.5" /> Back to Assessment
        </Link>
      }
    >
      <div className="space-y-4">
        {error && (
          <div className="rounded-xl bg-danger-soft px-4 py-3 text-sm font-semibold text-danger">
            {error}
          </div>
        )}

        <div className="overflow-hidden rounded-2xl border border-subtle bg-surface shadow-xs">
          {loading ? (
            <p className="p-6 text-sm text-ink-muted">Loading results...</p>
          ) : rows.length === 0 ? (
            <p className="p-8 text-center text-sm text-ink-muted">
              No candidate attempts recorded yet.
            </p>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-left text-sm">
                <thead className="border-b border-subtle bg-elevated/70 text-xs font-bold uppercase tracking-wider text-ink-muted">
                  <tr>
                    <th className="px-6 py-3.5">Candidate</th>
                    <th className="px-6 py-3.5">Attempt</th>
                    <th className="px-6 py-3.5">Submission</th>
                    <th className="px-6 py-3.5">Score</th>
                    <th className="px-6 py-3.5 text-right">Details</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-subtle">
                  {rows.map((row) => {
                    const expanded = expandedId === row.attempt_id;
                    return (
                      <Fragment key={row.attempt_id}>
                        <tr className="hover:bg-elevated/30">
                          <td className="px-6 py-4 font-semibold text-ink">
                            {row.candidate_email}
                          </td>
                          <td className="px-6 py-4">
                            <StatusBadge status={row.attempt_status} />
                          </td>
                          <td className="px-6 py-4">
                            {row.submission_status ? (
                              <StatusBadge status={row.submission_status} />
                            ) : (
                              <span className="text-xs text-ink-muted">Not submitted</span>
                            )}
                          </td>
                          <td className="px-6 py-4 font-extrabold text-ink">
                            {row.score !== null ? row.score : "—"}
                          </td>
                          <td className="px-6 py-4 text-right">
                            {row.submission_id && (
                              <button
                                type="button"
                                onClick={() =>
                                  setExpandedId(expanded ? null : row.attempt_id)
                                }
                                className="cursor-pointer rounded-full border border-subtle bg-elevated px-3.5 py-1 text-xs font-bold text-ink hover:border-strong"
                              >
                                {expanded ? "Hide Breakdown" : "Grade / Breakdown"}
                              </button>
                            )}
                          </td>
                        </tr>

                        {expanded && row.submission_id && (
                          <tr key={`${row.attempt_id}-detail`} className="bg-elevated/40">
                            <td colSpan={5} className="px-6 py-4">
                              <div className="space-y-2.5">
                                {(detail?.questions ?? []).map((q) => {
                                  const entry = row.scores[q.id];
                                  if (!entry) return null;
                                  const key = `${row.submission_id}:${q.id}`;
                                  const canManualGrade =
                                    q.question_type === "descriptive" ||
                                    q.question_type === "file_upload";
                                  return (
                                    <div
                                      key={q.id}
                                      className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-subtle bg-surface px-4 py-3 text-xs"
                                    >
                                      <div>
                                        <span className="font-extrabold text-accent-text">
                                          Q{q.position}
                                        </span>{" "}
                                        <span className="font-bold uppercase text-ink-muted">
                                          ({q.question_type})
                                        </span>{" "}
                                        <span className="font-semibold text-ink">
                                          {String(q.prompt.text ?? "").slice(0, 70)}
                                        </span>
                                      </div>

                                      <div className="flex items-center gap-3">
                                        <StatusBadge status={entry.status} />
                                        <span className="font-bold text-ink">
                                          {entry.score ?? "—"} / {q.max_score}
                                        </span>

                                        {canManualGrade && entry.answered && (
                                          <div className="flex items-center gap-1.5">
                                            <input
                                              type="number"
                                              step="0.5"
                                              min="0"
                                              max={q.max_score}
                                              value={
                                                gradeDrafts[key] ??
                                                (entry.score !== null ? String(entry.score) : "")
                                              }
                                              onChange={(e) =>
                                                setGradeDrafts((prev) => ({
                                                  ...prev,
                                                  [key]: e.target.value,
                                                }))
                                              }
                                              placeholder="Score"
                                              className="w-20 rounded-lg border border-strong bg-input px-2.5 py-1 text-xs text-ink"
                                            />
                                            <button
                                              type="button"
                                              disabled={savingKey === key}
                                              onClick={() =>
                                                void handleSaveGrade(row.submission_id!, q.id)
                                              }
                                              className="inline-flex cursor-pointer items-center gap-1 rounded-full bg-accent px-3 py-1 text-xs font-bold text-on-accent hover:bg-accent-hover disabled:opacity-60"
                                            >
                                              <Check className="h-3 w-3" /> Save
                                            </button>
                                          </div>
                                        )}
                                      </div>
                                    </div>
                                  );
                                })}
                              </div>
                            </td>
                          </tr>
                        )}
                      </Fragment>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>
    </AppShell>
  );
}
