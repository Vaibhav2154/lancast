import { useCallback, useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { ArrowRight, Clock, Eye, PlayCircle } from "lucide-react";
import { AppShell } from "../components/AppShell";
import { StatusBadge } from "../components/StatusBadge";
import {
  getMyAssessments,
  getMyAttempts,
  MyAssessment,
  MyAttempt,
  startOrResumeAttempt,
} from "../lib/api";

function formatTimestamp(iso: string | null): string {
  if (!iso) return "—";
  const d = new Date(iso);
  return Number.isNaN(d.getTime()) ? "—" : d.toLocaleString();
}

export function CandidateHome() {
  const navigate = useNavigate();
  const [assessments, setAssessments] = useState<MyAssessment[]>([]);
  const [attempts, setAttempts] = useState<MyAttempt[]>([]);
  const [loading, setLoading] = useState(true);
  const [startingId, setStartingId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [activeList, historyList] = await Promise.all([
        getMyAssessments(),
        getMyAttempts(),
      ]);
      setAssessments(activeList);
      setAttempts(historyList);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to load assessments");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  async function handleStart(item: MyAssessment) {
    setStartingId(item.assessment_id);
    setError(null);
    try {
      const attempt = await startOrResumeAttempt(item.tenant_id, item.assessment_id);
      navigate(`/exam/${attempt.id}`, { state: { initialAttempt: attempt, title: item.title } });
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Could not start assessment");
    } finally {
      setStartingId(null);
    }
  }

  return (
    <AppShell kicker="Candidate Portal" title="My Assessments">
      <div className="space-y-8">
        {error && (
          <div className="rounded-xl bg-danger-soft px-4 py-3 text-sm font-semibold text-danger">
            {error}
          </div>
        )}

        <section className="space-y-4">
          <h2 className="text-sm font-extrabold uppercase tracking-wider text-ink-muted">
            Active Assessments
          </h2>

          {loading ? (
            <div className="rounded-2xl border border-subtle bg-surface p-8 text-sm text-ink-muted">
              Loading enrolled assessments...
            </div>
          ) : assessments.length === 0 ? (
            <div className="rounded-2xl border border-subtle bg-surface p-10 text-center">
              <p className="text-base font-bold text-ink">No active assessments right now</p>
              <p className="mt-1 text-sm text-ink-muted">
                Once an organizer enrolls you and starts an assessment, it will appear here.
              </p>
            </div>
          ) : (
            <div className="grid gap-5 md:grid-cols-2">
              {assessments.map((item) => {
                const busy = startingId === item.assessment_id;
                const exhausted = !item.can_start && item.attempts_used >= item.max_attempts;
                return (
                  <div
                    key={item.assessment_id}
                    className="flex flex-col justify-between rounded-2xl border border-subtle bg-surface p-6 shadow-xs transition hover:border-accent/50"
                  >
                    <div>
                      <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
                        <div className="flex items-center gap-2">
                          <StatusBadge status="active" />
                          {exhausted && (
                            <StatusBadge
                              status={item.latest_submission_status ?? "submitted"}
                              label={
                                item.latest_submission_status === "scored"
                                  ? "Completed"
                                  : undefined
                              }
                            />
                          )}
                        </div>
                        <span className="font-mono text-xs text-ink-muted">
                          Tenant {item.tenant_id.slice(0, 8)}
                        </span>
                      </div>

                      <h3 className="mb-2 text-lg font-extrabold text-ink">{item.title}</h3>
                      <p className="mb-4 text-sm leading-relaxed text-ink-secondary">
                        {item.description || "Ready to begin. Your timer is enforced by the server."}
                      </p>

                      <div className="mb-5 flex flex-wrap items-center gap-x-4 gap-y-2 rounded-xl border border-subtle bg-elevated/50 px-3.5 py-2.5 text-xs">
                        <span className="inline-flex items-center gap-1 font-semibold text-ink-secondary">
                          <Clock className="h-3.5 w-3.5 text-ink-muted" />
                          {item.duration_minutes} min
                        </span>
                        <span className="font-semibold text-ink-secondary">
                          Attempts: {item.attempts_used} / {item.max_attempts}
                        </span>
                        {item.latest_submission_status && (
                          <span className="ml-auto font-extrabold text-ink">
                            Latest: {item.latest_score ?? 0} / {item.max_score}
                          </span>
                        )}
                      </div>
                    </div>

                    {item.active_attempt_id ? (
                      <button
                        type="button"
                        disabled={busy}
                        onClick={() => void handleStart(item)}
                        className="inline-flex w-full cursor-pointer items-center justify-center gap-2 rounded-full bg-accent px-5 py-3 text-sm font-bold text-on-accent shadow-sm transition hover:bg-accent-hover disabled:opacity-60"
                      >
                        <PlayCircle className="h-4 w-4" />
                        {busy ? "Resuming Exam..." : "Resume Assessment"}
                        <ArrowRight className="h-4 w-4" />
                      </button>
                    ) : item.can_start ? (
                      <button
                        type="button"
                        disabled={busy}
                        onClick={() => void handleStart(item)}
                        className="inline-flex w-full cursor-pointer items-center justify-center gap-2 rounded-full bg-accent px-5 py-3 text-sm font-bold text-on-accent shadow-sm transition hover:bg-accent-hover disabled:opacity-60"
                      >
                        <PlayCircle className="h-4 w-4" />
                        {busy
                          ? "Opening Exam..."
                          : item.attempts_used > 0
                            ? "Start New Attempt"
                            : "Start Assessment"}
                        <ArrowRight className="h-4 w-4" />
                      </button>
                    ) : item.latest_attempt_id ? (
                      <Link
                        to={`/exam/${item.latest_attempt_id}`}
                        state={{ title: item.title }}
                        className="inline-flex w-full items-center justify-center gap-2 rounded-full border border-accent-border bg-accent-soft px-5 py-3 text-sm font-bold text-accent-text transition hover:bg-accent/15"
                      >
                        <Eye className="h-4 w-4" />
                        View Result
                        <ArrowRight className="h-4 w-4" />
                      </Link>
                    ) : (
                      <button
                        type="button"
                        disabled
                        className="inline-flex w-full items-center justify-center rounded-full border border-subtle bg-elevated px-5 py-3 text-sm font-bold text-ink-muted opacity-70"
                      >
                        Assessment Closed
                      </button>
                    )}
                  </div>
                );
              })}
            </div>
          )}
        </section>

        <section className="space-y-4">
          <h2 className="text-sm font-extrabold uppercase tracking-wider text-ink-muted">
            Past Attempts & Submissions
          </h2>

          <div className="overflow-hidden rounded-2xl border border-subtle bg-surface shadow-xs">
            {loading ? (
              <p className="p-6 text-sm text-ink-muted">Loading attempt history...</p>
            ) : attempts.length === 0 ? (
              <p className="p-8 text-center text-sm text-ink-muted">
                You have not started any attempts yet.
              </p>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-left text-sm">
                  <thead className="border-b border-subtle bg-elevated/70 text-xs font-bold uppercase tracking-wider text-ink-muted">
                    <tr>
                      <th className="px-6 py-3.5">Assessment</th>
                      <th className="px-6 py-3.5">Attempt</th>
                      <th className="px-6 py-3.5">Evaluation</th>
                      <th className="px-6 py-3.5">Score</th>
                      <th className="px-6 py-3.5">Submitted</th>
                      <th className="px-6 py-3.5 text-right">Action</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-subtle">
                    {attempts.map((att) => {
                      const canResume =
                        att.attempt_status === "in_progress" &&
                        att.assessment_status === "active";
                      return (
                        <tr key={att.attempt_id} className="hover:bg-elevated/30">
                          <td className="px-6 py-4">
                            <div className="flex flex-wrap items-center gap-2">
                              <span className="font-bold text-ink">{att.assessment_title}</span>
                              <StatusBadge status={att.assessment_status} />
                            </div>
                          </td>
                          <td className="px-6 py-4">
                            <StatusBadge status={att.attempt_status} />
                          </td>
                          <td className="px-6 py-4">
                            {att.submission_status ? (
                              <StatusBadge status={att.submission_status} />
                            ) : (
                              <span className="text-xs text-ink-muted">In progress</span>
                            )}
                          </td>
                          <td className="px-6 py-4 font-extrabold text-ink">
                            {att.score !== null ? `${att.score} / ${att.max_score}` : "—"}
                          </td>
                          <td className="px-6 py-4 text-xs text-ink-secondary">
                            {formatTimestamp(att.submitted_at ?? att.started_at)}
                          </td>
                          <td className="px-6 py-4 text-right">
                            <Link
                              to={`/exam/${att.attempt_id}`}
                              state={{ title: att.assessment_title }}
                              className="inline-flex items-center gap-1 rounded-full border border-subtle bg-elevated px-3.5 py-1.5 text-xs font-bold text-ink hover:border-strong"
                            >
                              {canResume ? "Resume" : "View Result"}
                              <ArrowRight className="h-3 w-3" />
                            </Link>
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </section>
      </div>
    </AppShell>
  );
}
