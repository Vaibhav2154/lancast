import { useCallback, useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { ArrowRight, PlayCircle } from "lucide-react";
import { AppShell } from "../components/AppShell";
import { StatusBadge } from "../components/StatusBadge";
import {
  getMyAssessments,
  MyAssessment,
  startOrResumeAttempt,
} from "../lib/api";

export function CandidateHome() {
  const navigate = useNavigate();
  const [assessments, setAssessments] = useState<MyAssessment[]>([]);
  const [loading, setLoading] = useState(true);
  const [startingId, setStartingId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      setAssessments(await getMyAssessments());
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
    <AppShell kicker="Candidate Portal" title="My Active Assessments">
      <div className="space-y-4">
        {error && (
          <div className="rounded-xl bg-danger-soft px-4 py-3 text-sm font-semibold text-danger">
            {error}
          </div>
        )}

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
              return (
                <div
                  key={item.assessment_id}
                  className="flex flex-col justify-between rounded-2xl border border-subtle bg-surface p-6 shadow-xs transition hover:border-accent/50"
                >
                  <div>
                    <div className="mb-3 flex items-center justify-between">
                      <StatusBadge status="active" />
                      <span className="font-mono text-xs text-ink-muted">
                        Tenant {item.tenant_id.slice(0, 8)}
                      </span>
                    </div>
                    <h2 className="mb-2 text-lg font-extrabold text-ink">{item.title}</h2>
                    <p className="mb-6 text-sm leading-relaxed text-ink-secondary">
                      {item.description || "Ready to begin. Your timer is enforced by the server."}
                    </p>
                  </div>

                  <button
                    type="button"
                    disabled={busy}
                    onClick={() => void handleStart(item)}
                    className="inline-flex w-full cursor-pointer items-center justify-center gap-2 rounded-full bg-accent px-5 py-3 text-sm font-bold text-on-accent shadow-sm transition hover:bg-accent-hover disabled:opacity-60"
                  >
                    <PlayCircle className="h-4 w-4" />
                    {busy ? "Opening Exam..." : "Start / Resume Assessment"}
                    <ArrowRight className="h-4 w-4" />
                  </button>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </AppShell>
  );
}
