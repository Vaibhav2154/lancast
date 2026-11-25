import { Fragment, useCallback, useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { ArrowLeft, Check, Download, FileText } from "lucide-react";
import { AppShell } from "../components/AppShell";
import { StatusBadge } from "../components/StatusBadge";
import { useAuth } from "../hooks/useAuth";
import {
  AssessmentDetail,
  downloadUploadedFile,
  exportAssessmentResultsCsv,
  getAssessmentDetail,
  getAssessmentResults,
  gradeSubmissionQuestion,
  OrganizerQuestion,
  ResultRow,
  ResultScoreEntry,
} from "../lib/api";

function formatBytes(bytes: number): string {
  if (!Number.isFinite(bytes) || bytes < 1024) return `${bytes || 0} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
}

function optionTextMap(prompt: Record<string, unknown>): Map<string, string> {
  const map = new Map<string, string>();
  if (Array.isArray(prompt.options)) {
    for (const opt of prompt.options) {
      if (opt && typeof opt === "object" && "id" in opt) {
        map.set(String((opt as { id: unknown }).id), String((opt as { text?: unknown }).text ?? ""));
      }
    }
  }
  return map;
}

function triggerBlobDownload(blob: Blob, filename: string) {
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
}

function ResponsePreview({
  question,
  response,
  entry,
  downloadingFileId,
  onDownloadFile,
}: {
  question: OrganizerQuestion;
  response: Record<string, unknown> | undefined;
  entry: ResultScoreEntry | undefined;
  downloadingFileId: string | null;
  onDownloadFile: (fileId: string, originalName: string) => void;
}) {
  if (!response || (entry && !entry.answered)) {
    return <p className="mt-2 italic text-ink-muted">No answer submitted.</p>;
  }

  if (question.question_type === "mcq") {
    const selected = String(response.selected ?? "");
    const label = optionTextMap(question.prompt).get(selected);
    return (
      <div className="mt-2 rounded-lg border border-subtle bg-elevated/50 px-3 py-2 text-xs text-ink">
        <span className="font-bold text-ink-muted">Selected:</span>{" "}
        <span className="font-mono font-bold text-accent-text">{selected}</span>
        {label ? <span className="text-ink-secondary"> — {label}</span> : null}
      </div>
    );
  }

  if (question.question_type === "multiple_select") {
    const selected = Array.isArray(response.selected) ? response.selected.map(String) : [];
    const options = optionTextMap(question.prompt);
    return (
      <div className="mt-2 flex flex-wrap items-center gap-1.5 rounded-lg border border-subtle bg-elevated/50 px-3 py-2 text-xs">
        <span className="font-bold text-ink-muted">Selected:</span>
        {selected.length === 0 ? (
          <span className="italic text-ink-muted">None</span>
        ) : (
          selected.map((id) => (
            <span
              key={id}
              className="rounded-md border border-subtle bg-surface px-2 py-0.5 font-semibold text-ink"
            >
              <span className="font-mono text-accent-text">{id}</span>
              {options.get(id) ? ` — ${options.get(id)}` : ""}
            </span>
          ))
        )}
      </div>
    );
  }

  if (question.question_type === "descriptive") {
    return (
      <div className="mt-2 whitespace-pre-wrap rounded-lg border border-subtle bg-elevated/60 p-3 text-xs leading-relaxed text-ink">
        {String(response.text ?? "")}
      </div>
    );
  }

  if (question.question_type === "coding") {
    const language = String(response.language ?? "code");
    const sourceCode = String(response.source_code ?? "");
    return (
      <div className="mt-2 space-y-1.5">
        <div className="flex flex-wrap items-center gap-2 text-[11px] text-ink-secondary">
          <span className="rounded-md border border-subtle bg-elevated px-2 py-0.5 font-mono font-bold text-ink">
            {language}
          </span>
          {entry?.passed != null && entry?.total != null && (
            <span className="font-semibold text-ink">
              {entry.passed}/{entry.total} test cases passed
            </span>
          )}
          {entry?.error && <span className="font-semibold text-danger">{entry.error}</span>}
        </div>
        <pre className="max-h-60 overflow-auto rounded-lg border border-subtle bg-elevated/70 p-3 font-mono text-xs leading-relaxed text-ink">
          {sourceCode || "(empty submission)"}
        </pre>
      </div>
    );
  }

  if (question.question_type === "file_upload") {
    const fileId = response.file_id ? String(response.file_id) : "";
    const originalName = String(response.original_name ?? "uploaded-file");
    const sizeBytes = Number(response.size_bytes ?? 0);
    const sha256 = response.sha256 ? String(response.sha256) : "";
    const downloading = downloadingFileId === fileId;
    return (
      <div className="mt-2 flex flex-wrap items-center justify-between gap-3 rounded-lg border border-subtle bg-elevated/60 px-3 py-2.5 text-xs">
        <div className="flex items-center gap-2.5">
          <FileText className="h-4 w-4 text-accent-text" />
          <div>
            <p className="font-bold text-ink">{originalName}</p>
            <p className="font-mono text-[11px] text-ink-muted">
              {formatBytes(sizeBytes)}
              {sha256 ? ` • sha256:${sha256.slice(0, 12)}…` : ""}
            </p>
          </div>
        </div>
        {fileId && (
          <button
            type="button"
            disabled={downloading}
            onClick={() => onDownloadFile(fileId, originalName)}
            className="inline-flex cursor-pointer items-center gap-1.5 rounded-full border border-strong bg-surface px-3 py-1 text-xs font-bold text-ink hover:bg-elevated disabled:opacity-60"
          >
            <Download className="h-3.5 w-3.5" />
            {downloading ? "Downloading..." : "Download File"}
          </button>
        )}
      </div>
    );
  }

  return null;
}

export function ResultsGradingPage() {
  const { assessmentId } = useParams<{ assessmentId: string }>();
  const { activeTenantId } = useAuth();

  const [detail, setDetail] = useState<AssessmentDetail | null>(null);
  const [rows, setRows] = useState<ResultRow[]>([]);
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [gradeDrafts, setGradeDrafts] = useState<Record<string, string>>({});
  const [loading, setLoading] = useState(true);
  const [savingKey, setSavingKey] = useState<string | null>(null);
  const [exportingCsv, setExportingCsv] = useState(false);
  const [downloadingFileId, setDownloadingFileId] = useState<string | null>(null);
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

  async function handleExportCsv() {
    if (!activeTenantId || !assessmentId) return;
    setExportingCsv(true);
    setError(null);
    try {
      const blob = await exportAssessmentResultsCsv(activeTenantId, assessmentId);
      const slug =
        (detail?.title ?? "assessment")
          .toLowerCase()
          .replace(/[^a-z0-9._-]+/g, "-")
          .replace(/^-+|-+$/g, "") || "assessment";
      triggerBlobDownload(blob, `${slug}-results.csv`);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to export CSV");
    } finally {
      setExportingCsv(false);
    }
  }

  async function handleDownloadFile(fileId: string, originalName: string) {
    if (!activeTenantId) return;
    setDownloadingFileId(fileId);
    setError(null);
    try {
      const blob = await downloadUploadedFile(activeTenantId, fileId);
      triggerBlobDownload(blob, originalName);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to download file");
    } finally {
      setDownloadingFileId(null);
    }
  }

  return (
    <AppShell
      kicker="Results & Grading"
      title={detail ? `${detail.title} — Results` : "Assessment Results"}
      actions={
        <div className="flex flex-wrap items-center gap-2">
          <button
            type="button"
            disabled={loading || exportingCsv || rows.length === 0}
            onClick={() => void handleExportCsv()}
            className="inline-flex cursor-pointer items-center gap-1.5 rounded-full bg-accent px-4 py-2 text-xs font-bold text-on-accent shadow-xs hover:bg-accent-hover disabled:cursor-not-allowed disabled:opacity-50"
          >
            <Download className="h-3.5 w-3.5" />
            {exportingCsv ? "Exporting..." : "Export CSV"}
          </button>
          <Link
            to={assessmentId ? `/organizer/assessments/${assessmentId}` : "/organizer"}
            className="inline-flex items-center gap-1.5 rounded-full border border-subtle bg-surface px-4 py-2 text-xs font-bold text-ink hover:bg-elevated"
          >
            <ArrowLeft className="h-3.5 w-3.5" /> Back to Assessment
          </Link>
        </div>
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
                    const canExpand =
                      Boolean(row.submission_id) ||
                      Object.keys(row.responses ?? {}).length > 0;
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
                            {canExpand && (
                              <button
                                type="button"
                                onClick={() =>
                                  setExpandedId(expanded ? null : row.attempt_id)
                                }
                                className="cursor-pointer rounded-full border border-subtle bg-elevated px-3.5 py-1 text-xs font-bold text-ink hover:border-strong"
                              >
                                {expanded
                                  ? "Hide Breakdown"
                                  : row.submission_id
                                    ? "Grade / Breakdown"
                                    : "View Responses"}
                              </button>
                            )}
                          </td>
                        </tr>

                        {expanded && canExpand && (
                          <tr key={`${row.attempt_id}-detail`} className="bg-elevated/40">
                            <td colSpan={5} className="px-6 py-4">
                              <div className="space-y-3">
                                {(detail?.questions ?? []).map((q) => {
                                  const entry = row.scores[q.id];
                                  const resp = row.responses?.[q.id];
                                  if (!entry && !resp) return null;
                                  const key = `${row.submission_id}:${q.id}`;
                                  const canManualGrade =
                                    Boolean(row.submission_id) &&
                                    (q.question_type === "descriptive" ||
                                      q.question_type === "file_upload");
                                  return (
                                    <div
                                      key={q.id}
                                      className="rounded-xl border border-subtle bg-surface px-4 py-3 text-xs"
                                    >
                                      <div className="flex flex-wrap items-center justify-between gap-3">
                                        <div>
                                          <span className="font-extrabold text-accent-text">
                                            Q{q.position}
                                          </span>{" "}
                                          <span className="font-bold uppercase text-ink-muted">
                                            ({q.question_type})
                                          </span>{" "}
                                          <span className="font-semibold text-ink">
                                            {String(q.prompt.text ?? "").slice(0, 120)}
                                          </span>
                                        </div>

                                        {entry && (
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
                                        )}
                                      </div>

                                      <ResponsePreview
                                        question={q}
                                        response={resp}
                                        entry={entry}
                                        downloadingFileId={downloadingFileId}
                                        onDownloadFile={(fileId, originalName) =>
                                          void handleDownloadFile(fileId, originalName)
                                        }
                                      />
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
