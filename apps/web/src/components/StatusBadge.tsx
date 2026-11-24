const VARIANT_MAP: Record<string, { label: string; badge: string; dot: string }> = {
  active: {
    label: "Active",
    badge: "bg-accent-soft text-accent-text border-accent-border",
    dot: "bg-accent",
  },
  ready: {
    label: "Ready",
    badge: "bg-accent-soft text-accent-text border-accent-border",
    dot: "bg-accent",
  },
  ok: {
    label: "Healthy",
    badge: "bg-accent-soft text-accent-text border-accent-border",
    dot: "bg-accent",
  },
  scored: {
    label: "Scored",
    badge: "bg-accent-soft text-accent-text border-accent-border",
    dot: "bg-accent",
  },
  submitted: {
    label: "Submitted",
    badge: "bg-accent-soft text-accent-text border-accent-border",
    dot: "bg-accent",
  },
  published: {
    label: "Published",
    badge: "bg-emerald-500/10 text-emerald-700 dark:text-emerald-300 border-emerald-500/30",
    dot: "bg-emerald-500",
  },
  in_progress: {
    label: "In Progress",
    badge: "bg-emerald-500/10 text-emerald-700 dark:text-emerald-300 border-emerald-500/30",
    dot: "bg-emerald-500",
  },
  draft: {
    label: "Draft",
    badge: "bg-elevated text-ink-secondary border-subtle",
    dot: "bg-ink-muted",
  },
  archived: {
    label: "Archived",
    badge: "bg-elevated text-ink-muted border-subtle",
    dot: "bg-ink-muted",
  },
  closed: {
    label: "Closed",
    badge: "bg-warn-soft text-warn border-warn/30",
    dot: "bg-warn",
  },
  evaluating: {
    label: "Evaluating",
    badge: "bg-warn-soft text-warn border-warn/30",
    dot: "bg-warn",
  },
  queued: {
    label: "Queued",
    badge: "bg-warn-soft text-warn border-warn/30",
    dot: "bg-warn",
  },
  pending_review: {
    label: "Pending Review",
    badge: "bg-warn-soft text-warn border-warn/30",
    dot: "bg-warn",
  },
  pending: {
    label: "Pending Grade",
    badge: "bg-warn-soft text-warn border-warn/30",
    dot: "bg-warn",
  },
  degraded: {
    label: "Degraded",
    badge: "bg-warn-soft text-warn border-warn/30",
    dot: "bg-warn",
  },
  expired: {
    label: "Expired",
    badge: "bg-danger-soft text-danger border-danger/30",
    dot: "bg-danger",
  },
  flagged: {
    label: "Flagged",
    badge: "bg-danger-soft text-danger border-danger/30",
    dot: "bg-danger",
  },
  failed: {
    label: "Failed",
    badge: "bg-danger-soft text-danger border-danger/30",
    dot: "bg-danger",
  },
  error: {
    label: "Error",
    badge: "bg-danger-soft text-danger border-danger/30",
    dot: "bg-danger",
  },
  unreachable: {
    label: "Unreachable",
    badge: "bg-danger-soft text-danger border-danger/30",
    dot: "bg-danger",
  },
};

export function StatusBadge({
  status,
  label,
}: {
  status: string;
  label?: string;
}) {
  const key = status.toLowerCase();
  const style = VARIANT_MAP[key] ?? {
    label: status,
    badge: "bg-elevated text-ink-secondary border-subtle",
    dot: "bg-ink-muted",
  };
  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full border px-3 py-0.5 text-xs font-bold whitespace-nowrap ${style.badge}`}
    >
      <span className={`h-1.5 w-1.5 rounded-full ${style.dot}`} />
      {label ?? style.label}
    </span>
  );
}
