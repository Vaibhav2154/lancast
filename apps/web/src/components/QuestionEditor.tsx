import { FormEvent, useState } from "react";
import { Plus, Trash2, X } from "lucide-react";
import { CodingLanguage, OrganizerQuestion, QuestionType } from "../lib/api";

const ALL_EXTENSIONS = [
  "pdf",
  "png",
  "jpg",
  "jpeg",
  "zip",
  "txt",
  "md",
  "csv",
  "py",
  "c",
  "cpp",
  "java",
];

const ALL_LANGUAGES: { id: CodingLanguage; label: string }[] = [
  { id: "python3", label: "Python 3" },
  { id: "c", label: "C" },
  { id: "cpp", label: "C++" },
  { id: "java", label: "Java" },
  { id: "javascript", label: "JavaScript" },
];

interface OptionItem {
  id: string;
  text: string;
}

interface CaseItem {
  stdin: string;
  expected_stdout: string;
}

export interface QuestionPayload {
  question_type: QuestionType;
  prompt: Record<string, unknown>;
  hidden_eval: Record<string, unknown>;
  max_score: number;
}

export function QuestionEditor({
  initial,
  onSave,
  onCancel,
  saving,
}: {
  initial?: OrganizerQuestion | null;
  onSave: (payload: QuestionPayload) => Promise<void>;
  onCancel: () => void;
  saving: boolean;
}) {
  const isEditing = Boolean(initial);

  const [questionType, setQuestionType] = useState<QuestionType>(
    initial?.question_type ?? "mcq"
  );
  const [maxScore, setMaxScore] = useState<number>(initial?.max_score ?? 1);
  const [text, setText] = useState<string>(String(initial?.prompt.text ?? ""));

  // MCQ / Multiple-select state
  const [options, setOptions] = useState<OptionItem[]>(() => {
    const raw = initial?.prompt.options;
    if (Array.isArray(raw) && raw.length >= 2) {
      return raw.map((o) => ({
        id: String((o as { id?: unknown }).id ?? ""),
        text: String((o as { text?: unknown }).text ?? ""),
      }));
    }
    return [
      { id: "a", text: "" },
      { id: "b", text: "" },
      { id: "c", text: "" },
      { id: "d", text: "" },
    ];
  });
  const [mcqCorrect, setMcqCorrect] = useState<string>(() =>
    typeof initial?.hidden_eval.correct === "string" ? initial.hidden_eval.correct : "a"
  );
  const [multiCorrect, setMultiCorrect] = useState<string[]>(() =>
    Array.isArray(initial?.hidden_eval.correct)
      ? initial.hidden_eval.correct.map(String)
      : ["a"]
  );
  const [multiScoring, setMultiScoring] = useState<"exact" | "partial">(() =>
    initial?.hidden_eval.scoring === "partial" ? "partial" : "exact"
  );

  // Descriptive state
  const [maxLength, setMaxLength] = useState<number>(() =>
    typeof initial?.prompt.max_length === "number" ? initial.prompt.max_length : 2000
  );
  const [rubric, setRubric] = useState<string>(() =>
    typeof initial?.hidden_eval.rubric === "string" ? initial.hidden_eval.rubric : ""
  );

  // File upload state
  const [allowedExtensions, setAllowedExtensions] = useState<string[]>(() =>
    Array.isArray(initial?.prompt.allowed_extensions)
      ? initial.prompt.allowed_extensions.map(String)
      : ["pdf", "txt", "py"]
  );
  const [maxSizeMb, setMaxSizeMb] = useState<number>(() =>
    typeof initial?.prompt.max_size_bytes === "number"
      ? Math.max(1, Math.round((initial.prompt.max_size_bytes / (1024 * 1024)) * 10) / 10)
      : 2
  );

  // Coding state
  const [languages, setLanguages] = useState<CodingLanguage[]>(() =>
    Array.isArray(initial?.prompt.languages)
      ? (initial.prompt.languages as CodingLanguage[])
      : ALL_LANGUAGES.map((l) => l.id)
  );
  const [sampleCases, setSampleCases] = useState<CaseItem[]>(() =>
    Array.isArray(initial?.prompt.sample_cases)
      ? initial.prompt.sample_cases.map((c) => ({
          stdin: String((c as { stdin?: unknown }).stdin ?? ""),
          expected_stdout: String((c as { expected_stdout?: unknown }).expected_stdout ?? ""),
        }))
      : [{ stdin: "", expected_stdout: "" }]
  );
  const [hiddenCases, setHiddenCases] = useState<CaseItem[]>(() =>
    Array.isArray(initial?.hidden_eval.test_cases) && initial.hidden_eval.test_cases.length > 0
      ? initial.hidden_eval.test_cases.map((c) => ({
          stdin: String((c as { stdin?: unknown }).stdin ?? ""),
          expected_stdout: String((c as { expected_stdout?: unknown }).expected_stdout ?? ""),
        }))
      : [{ stdin: "", expected_stdout: "" }]
  );
  const [cpuTimeLimit, setCpuTimeLimit] = useState<number>(() =>
    typeof initial?.hidden_eval.cpu_time_limit_sec === "number"
      ? initial.hidden_eval.cpu_time_limit_sec
      : 2
  );
  const [memoryLimitMb, setMemoryLimitMb] = useState<number>(() =>
    typeof initial?.hidden_eval.memory_limit_mb === "number"
      ? initial.hidden_eval.memory_limit_mb
      : 256
  );

  const [error, setError] = useState<string | null>(null);

  function toggleExtension(ext: string) {
    setAllowedExtensions((prev) =>
      prev.includes(ext) ? prev.filter((x) => x !== ext) : [...prev, ext]
    );
  }

  function toggleLanguage(lang: CodingLanguage) {
    setLanguages((prev) =>
      prev.includes(lang) ? prev.filter((x) => x !== lang) : [...prev, lang]
    );
  }

  function toggleMultiCorrect(id: string) {
    setMultiCorrect((prev) =>
      prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id]
    );
  }

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);

    if (!text.trim()) {
      setError("Question prompt text is required.");
      return;
    }
    if (maxScore <= 0) {
      setError("Max score must be greater than 0.");
      return;
    }

    let prompt: Record<string, unknown> = {};
    let hidden_eval: Record<string, unknown> = {};

    if (questionType === "mcq" || questionType === "multiple_select") {
      const cleaned = options
        .map((o) => ({ id: o.id.trim(), text: o.text.trim() }))
        .filter((o) => o.id && o.text);
      if (cleaned.length < 2) {
        setError("Provide at least 2 complete options (ID and text).");
        return;
      }
      const ids = new Set(cleaned.map((o) => o.id));
      if (ids.size !== cleaned.length) {
        setError("Option IDs must be unique.");
        return;
      }
      prompt = { text: text.trim(), options: cleaned };
      if (questionType === "mcq") {
        if (!ids.has(mcqCorrect)) {
          setError("Select a valid correct option.");
          return;
        }
        hidden_eval = { correct: mcqCorrect };
      } else {
        const validCorrect = multiCorrect.filter((id) => ids.has(id));
        if (validCorrect.length === 0) {
          setError("Select at least one correct option.");
          return;
        }
        hidden_eval = { correct: validCorrect, scoring: multiScoring };
      }
    } else if (questionType === "descriptive") {
      prompt = { text: text.trim(), max_length: Number(maxLength) };
      hidden_eval = { rubric: rubric.trim() };
    } else if (questionType === "file_upload") {
      if (allowedExtensions.length === 0) {
        setError("Select at least one allowed file extension.");
        return;
      }
      prompt = {
        text: text.trim(),
        allowed_extensions: allowedExtensions,
        max_size_bytes: Math.round(maxSizeMb * 1024 * 1024),
      };
      hidden_eval = {};
    } else if (questionType === "coding") {
      if (languages.length === 0) {
        setError("Select at least one programming language.");
        return;
      }
      if (hiddenCases.length === 0) {
        setError("At least one hidden test case is required.");
        return;
      }
      prompt = {
        text: text.trim(),
        languages,
        sample_cases: sampleCases.filter((c) => c.stdin !== "" || c.expected_stdout !== ""),
      };
      hidden_eval = {
        test_cases: hiddenCases,
        cpu_time_limit_sec: Number(cpuTimeLimit),
        memory_limit_mb: Number(memoryLimitMb),
      };
    }

    try {
      await onSave({ question_type: questionType, prompt, hidden_eval, max_score: Number(maxScore) });
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to save question");
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4 backdrop-blur-xs">
      <div className="max-h-[90vh] w-full max-w-2xl overflow-y-auto rounded-2xl border border-subtle bg-surface p-6 shadow-2xl">
        <div className="mb-5 flex items-center justify-between border-b border-subtle pb-3">
          <div>
            <p className="text-xs font-bold uppercase tracking-wider text-accent-text">
              {isEditing ? "Edit Question" : "Add Question"}
            </p>
            <h2 className="text-lg font-extrabold text-ink">
              {isEditing ? `Question #${initial?.position}` : "New Assessment Question"}
            </h2>
          </div>
          <button
            type="button"
            onClick={onCancel}
            className="cursor-pointer rounded-full p-1.5 text-ink-muted hover:bg-elevated hover:text-ink"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="grid gap-4 sm:grid-cols-2">
            <div>
              <label className="mb-1 block text-xs font-semibold text-ink-secondary">
                Question Type
              </label>
              <select
                value={questionType}
                disabled={isEditing}
                onChange={(e) => setQuestionType(e.target.value as QuestionType)}
                className="w-full rounded-xl border border-strong bg-input px-3 py-2 text-sm text-ink disabled:opacity-60"
              >
                <option value="mcq">Single-Choice MCQ</option>
                <option value="multiple_select">Multiple Select</option>
                <option value="descriptive">Descriptive</option>
                <option value="file_upload">File Upload</option>
                <option value="coding">Programming (Judge0)</option>
              </select>
            </div>

            <div>
              <label className="mb-1 block text-xs font-semibold text-ink-secondary">
                Max Score
              </label>
              <input
                type="number"
                step="0.5"
                min="0.5"
                max="1000"
                required
                value={maxScore}
                onChange={(e) => setMaxScore(Number(e.target.value))}
                className="w-full rounded-xl border border-strong bg-input px-3 py-2 text-sm text-ink"
              />
            </div>
          </div>

          <div>
            <label className="mb-1 block text-xs font-semibold text-ink-secondary">
              Question Prompt
            </label>
            <textarea
              rows={3}
              required
              value={text}
              onChange={(e) => setText(e.target.value)}
              placeholder="Enter clear question instructions..."
              className="w-full rounded-xl border border-strong bg-input px-3.5 py-2.5 text-sm text-ink"
            />
          </div>

          {(questionType === "mcq" || questionType === "multiple_select") && (
            <div className="space-y-3 rounded-xl border border-subtle bg-elevated/60 p-4">
              <div className="flex items-center justify-between">
                <span className="text-xs font-bold uppercase tracking-wider text-ink-secondary">
                  Answer Options
                </span>
                {questionType === "multiple_select" && (
                  <select
                    value={multiScoring}
                    onChange={(e) => setMultiScoring(e.target.value as "exact" | "partial")}
                    className="rounded-lg border border-strong bg-surface px-2.5 py-1 text-xs font-semibold text-ink"
                  >
                    <option value="exact">Exact match</option>
                    <option value="partial">Partial credit</option>
                  </select>
                )}
              </div>

              {options.map((opt, idx) => (
                <div key={idx} className="flex items-center gap-2">
                  {questionType === "mcq" ? (
                    <input
                      type="radio"
                      name="mcq-correct"
                      checked={mcqCorrect === opt.id}
                      onChange={() => setMcqCorrect(opt.id)}
                      title="Mark as correct answer"
                      className="h-4 w-4 accent-emerald-600"
                    />
                  ) : (
                    <input
                      type="checkbox"
                      checked={multiCorrect.includes(opt.id)}
                      onChange={() => toggleMultiCorrect(opt.id)}
                      title="Include in correct answers"
                      className="h-4 w-4 accent-emerald-600"
                    />
                  )}
                  <input
                    type="text"
                    value={opt.id}
                    onChange={(e) => {
                      const val = e.target.value;
                      setOptions((prev) =>
                        prev.map((item, i) => (i === idx ? { ...item, id: val } : item))
                      );
                    }}
                    placeholder="id"
                    className="w-16 rounded-lg border border-strong bg-surface px-2.5 py-1.5 text-xs font-mono text-ink"
                  />
                  <input
                    type="text"
                    value={opt.text}
                    onChange={(e) => {
                      const val = e.target.value;
                      setOptions((prev) =>
                        prev.map((item, i) => (i === idx ? { ...item, text: val } : item))
                      );
                    }}
                    placeholder={`Option ${idx + 1} text`}
                    className="flex-1 rounded-lg border border-strong bg-surface px-3 py-1.5 text-sm text-ink"
                  />
                  {options.length > 2 && (
                    <button
                      type="button"
                      onClick={() => setOptions((prev) => prev.filter((_, i) => i !== idx))}
                      className="cursor-pointer rounded-lg p-1.5 text-ink-muted hover:text-danger"
                    >
                      <Trash2 className="h-4 w-4" />
                    </button>
                  )}
                </div>
              ))}

              {options.length < 10 && (
                <button
                  type="button"
                  onClick={() =>
                    setOptions((prev) => [
                      ...prev,
                      { id: String.fromCharCode(97 + prev.length), text: "" },
                    ])
                  }
                  className="inline-flex cursor-pointer items-center gap-1.5 text-xs font-bold text-accent-text hover:underline"
                >
                  <Plus className="h-3.5 w-3.5" /> Add Option
                </button>
              )}
            </div>
          )}

          {questionType === "descriptive" && (
            <div className="grid gap-4 rounded-xl border border-subtle bg-elevated/60 p-4 sm:grid-cols-2">
              <div>
                <label className="mb-1 block text-xs font-semibold text-ink-secondary">
                  Max Characters
                </label>
                <input
                  type="number"
                  min={1}
                  max={20000}
                  value={maxLength}
                  onChange={(e) => setMaxLength(Number(e.target.value))}
                  className="w-full rounded-xl border border-strong bg-surface px-3 py-2 text-sm text-ink"
                />
              </div>
              <div>
                <label className="mb-1 block text-xs font-semibold text-ink-secondary">
                  Grading Rubric (Organizer-only)
                </label>
                <input
                  type="text"
                  value={rubric}
                  onChange={(e) => setRubric(e.target.value)}
                  placeholder="Key points for manual grading"
                  className="w-full rounded-xl border border-strong bg-surface px-3 py-2 text-sm text-ink"
                />
              </div>
            </div>
          )}

          {questionType === "file_upload" && (
            <div className="space-y-3 rounded-xl border border-subtle bg-elevated/60 p-4">
              <div>
                <label className="mb-2 block text-xs font-semibold text-ink-secondary">
                  Allowed Extensions
                </label>
                <div className="flex flex-wrap gap-2">
                  {ALL_EXTENSIONS.map((ext) => {
                    const checked = allowedExtensions.includes(ext);
                    return (
                      <button
                        key={ext}
                        type="button"
                        onClick={() => toggleExtension(ext)}
                        className={`cursor-pointer rounded-full border px-3 py-1 text-xs font-bold transition ${
                          checked
                            ? "border-accent-border bg-accent-soft text-accent-text"
                            : "border-subtle bg-surface text-ink-secondary"
                        }`}
                      >
                        .{ext}
                      </button>
                    );
                  })}
                </div>
              </div>
              <div>
                <label className="mb-1 block text-xs font-semibold text-ink-secondary">
                  Max File Size (MB, up to 10)
                </label>
                <input
                  type="number"
                  step="0.5"
                  min="0.5"
                  max="10"
                  value={maxSizeMb}
                  onChange={(e) => setMaxSizeMb(Number(e.target.value))}
                  className="w-36 rounded-xl border border-strong bg-surface px-3 py-2 text-sm text-ink"
                />
              </div>
            </div>
          )}

          {questionType === "coding" && (
            <div className="space-y-4 rounded-xl border border-subtle bg-elevated/60 p-4">
              <div>
                <label className="mb-2 block text-xs font-semibold text-ink-secondary">
                  Allowed Languages
                </label>
                <div className="flex flex-wrap gap-2">
                  {ALL_LANGUAGES.map((lang) => {
                    const checked = languages.includes(lang.id);
                    return (
                      <button
                        key={lang.id}
                        type="button"
                        onClick={() => toggleLanguage(lang.id)}
                        className={`cursor-pointer rounded-full border px-3 py-1 text-xs font-bold transition ${
                          checked
                            ? "border-accent-border bg-accent-soft text-accent-text"
                            : "border-subtle bg-surface text-ink-secondary"
                        }`}
                      >
                        {lang.label}
                      </button>
                    );
                  })}
                </div>
              </div>

              <div className="grid gap-4 sm:grid-cols-2">
                <div>
                  <label className="mb-1 block text-xs font-semibold text-ink-secondary">
                    CPU Limit (seconds, 0.5–10)
                  </label>
                  <input
                    type="number"
                    step="0.5"
                    min="0.5"
                    max="10"
                    value={cpuTimeLimit}
                    onChange={(e) => setCpuTimeLimit(Number(e.target.value))}
                    className="w-full rounded-xl border border-strong bg-surface px-3 py-2 text-sm text-ink"
                  />
                </div>
                <div>
                  <label className="mb-1 block text-xs font-semibold text-ink-secondary">
                    Memory Limit (MB, 32–512)
                  </label>
                  <input
                    type="number"
                    step="32"
                    min="32"
                    max="512"
                    value={memoryLimitMb}
                    onChange={(e) => setMemoryLimitMb(Number(e.target.value))}
                    className="w-full rounded-xl border border-strong bg-surface px-3 py-2 text-sm text-ink"
                  />
                </div>
              </div>

              <CaseListEditor
                title="Public Sample Cases (Visible to Candidates)"
                cases={sampleCases}
                onChange={setSampleCases}
                max={5}
              />
              <CaseListEditor
                title="Hidden Evaluation Test Cases (Server-Only)"
                cases={hiddenCases}
                onChange={setHiddenCases}
                min={1}
                max={50}
              />
            </div>
          )}

          {error && (
            <p className="rounded-xl bg-danger-soft px-3.5 py-2.5 text-xs font-semibold text-danger">
              {error}
            </p>
          )}

          <div className="flex justify-end gap-2.5 border-t border-subtle pt-4">
            <button
              type="button"
              onClick={onCancel}
              className="cursor-pointer rounded-full border border-strong bg-surface px-5 py-2 text-sm font-semibold text-ink hover:bg-elevated"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={saving}
              className="cursor-pointer rounded-full bg-accent px-6 py-2 text-sm font-bold text-on-accent shadow-sm hover:bg-accent-hover disabled:opacity-60"
            >
              {saving ? "Saving..." : isEditing ? "Save Changes" : "Add Question"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

function CaseListEditor({
  title,
  cases,
  onChange,
  min = 0,
  max = 10,
}: {
  title: string;
  cases: CaseItem[];
  onChange: (next: CaseItem[]) => void;
  min?: number;
  max?: number;
}) {
  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between">
        <span className="text-xs font-bold text-ink-secondary">{title}</span>
        {cases.length < max && (
          <button
            type="button"
            onClick={() => onChange([...cases, { stdin: "", expected_stdout: "" }])}
            className="inline-flex cursor-pointer items-center gap-1 text-xs font-bold text-accent-text hover:underline"
          >
            <Plus className="h-3.5 w-3.5" /> Add Case
          </button>
        )}
      </div>
      {cases.map((c, idx) => (
        <div key={idx} className="grid grid-cols-12 items-start gap-2">
          <textarea
            rows={2}
            value={c.stdin}
            onChange={(e) =>
              onChange(cases.map((item, i) => (i === idx ? { ...item, stdin: e.target.value } : item)))
            }
            placeholder="stdin"
            className="col-span-5 rounded-lg border border-strong bg-surface p-2 font-mono text-xs text-ink"
          />
          <textarea
            rows={2}
            value={c.expected_stdout}
            onChange={(e) =>
              onChange(
                cases.map((item, i) =>
                  i === idx ? { ...item, expected_stdout: e.target.value } : item
                )
              )
            }
            placeholder="expected stdout"
            className="col-span-6 rounded-lg border border-strong bg-surface p-2 font-mono text-xs text-ink"
          />
          <div className="col-span-1 flex justify-end pt-1">
            {cases.length > min && (
              <button
                type="button"
                onClick={() => onChange(cases.filter((_, i) => i !== idx))}
                className="cursor-pointer rounded-lg p-1 text-ink-muted hover:text-danger"
              >
                <Trash2 className="h-4 w-4" />
              </button>
            )}
          </div>
        </div>
      ))}
    </div>
  );
}
