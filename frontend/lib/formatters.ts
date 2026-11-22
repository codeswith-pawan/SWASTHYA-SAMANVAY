import { Priority, ReferralStatus } from "./types";

export function formatDateTime(value: string | null | undefined): string {
  if (!value) return "—";
  try {
    const d = new Date(value);
    if (isNaN(d.getTime())) return value;
    return d.toLocaleString("en-IN", {
      day: "2-digit",
      month: "short",
      year: "numeric",
      hour: "2-digit",
      minute: "2-digit",
      hour12: true,
    });
  } catch {
    return value;
  }
}

export function formatDate(value: string | null | undefined): string {
  if (!value) return "—";
  try {
    const d = new Date(value);
    if (isNaN(d.getTime())) return value;
    return d.toLocaleDateString("en-IN", {
      day: "2-digit",
      month: "short",
      year: "numeric",
    });
  } catch {
    return value;
  }
}

export function formatDistance(km: number | null | undefined): string {
  if (km === null || km === undefined || isNaN(km)) return "N/A";
  return `${km.toFixed(1)} km`;
}

export function formatPercent(value: number | null | undefined, decimals = 1): string {
  if (value === null || value === undefined || isNaN(value)) return "—";
  const num = value > 1 && value <= 100 ? value : value * 100;
  return `${num.toFixed(decimals)}%`;
}

export function formatModelFitScore(value: unknown): string {
  if (value === null || value === undefined) return "Unavailable";
  const num = Number(value);
  if (isNaN(num) || num < 0) return "Unavailable";
  const pct = num <= 1 ? num * 100 : num;
  return `${pct.toFixed(1)}%`;
}

export function getPriorityStyles(priority: Priority | string): {
  badge: string;
  dot: string;
  label: string;
} {
  const p = (priority || "").toLowerCase();
  if (p === "critical") {
    return {
      badge: "bg-rose-500/10 text-rose-400 border border-rose-500/20",
      dot: "bg-rose-500",
      label: "Critical Priority",
    };
  }
  if (p === "urgent") {
    return {
      badge: "bg-amber-500/10 text-amber-400 border border-amber-500/20",
      dot: "bg-amber-500",
      label: "Urgent Priority",
    };
  }
  return {
    badge: "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20",
    dot: "bg-emerald-500",
    label: "Stable",
  };
}

export type StatusInfo = {
  label: string;
  badge: string;
  border: string;
  icon: string;
  description: string;
  stageIndex: number; // 0 to 5 for standard linear lifecycle; -1 for terminal/abnormal
};

export const REFERRAL_STATUS_MAP: Record<ReferralStatus, StatusInfo> = {
  PENDING: {
    label: "Pending Review",
    badge: "bg-amber-500/10 text-amber-400 border-amber-500/30",
    border: "border-amber-500/30",
    icon: "⏳",
    description: "Awaiting clinical acceptance from receiving hospital",
    stageIndex: 0,
  },
  ACCEPTED: {
    label: "Accepted & Reserved",
    badge: "bg-blue-500/10 text-blue-400 border-blue-500/30",
    border: "border-blue-500/30",
    icon: "✓",
    description: "Referral accepted; bed reserved in inventory",
    stageIndex: 1,
  },
  IN_TRANSIT: {
    label: "In Transit",
    badge: "bg-indigo-500/10 text-indigo-300 border-indigo-500/30",
    border: "border-indigo-500/30",
    icon: "🚑",
    description: "Ambulance dispatched; patient actively en route",
    stageIndex: 2,
  },
  ARRIVED: {
    label: "Patient Arrived",
    badge: "bg-cyan-500/10 text-cyan-400 border-cyan-500/30",
    border: "border-cyan-500/30",
    icon: "🏥",
    description: "Patient arrived at destination hospital intake",
    stageIndex: 3,
  },
  TREATMENT_ACTIVE: {
    label: "Treatment Active",
    badge: "bg-purple-500/10 text-purple-300 border-purple-500/30",
    border: "border-purple-500/30",
    icon: "🩺",
    description: "Patient admitted to reserved ward; treatment in progress",
    stageIndex: 4,
  },
  IN_TREATMENT: {
    label: "In Treatment",
    badge: "bg-purple-500/10 text-purple-300 border-purple-500/30",
    border: "border-purple-500/30",
    icon: "🩺",
    description: "Patient admitted to reserved ward; treatment in progress",
    stageIndex: 4,
  },
  COMPLETED: {
    label: "Completed",
    badge: "bg-emerald-500/10 text-emerald-400 border-emerald-500/30",
    border: "border-emerald-500/30",
    icon: "✓",
    description: "Treatment finished; referral discharged and bed released",
    stageIndex: 5,
  },
  REJECTED: {
    label: "Rejected",
    badge: "bg-rose-500/10 text-rose-400 border-rose-500/30",
    border: "border-rose-500/30",
    icon: "✕",
    description: "Referral declined by destination facility",
    stageIndex: -1,
  },
  TRANSFERRED: {
    label: "Transferred Out",
    badge: "bg-slate-500/10 text-slate-300 border-slate-500/30",
    border: "border-slate-500/30",
    icon: "↗",
    description: "Transferred further to tertiary / quaternary center",
    stageIndex: -1,
  },
  DIED: {
    label: "Patient Deceased",
    badge: "bg-red-950/40 text-red-400 border-red-800/40",
    border: "border-red-800/40",
    icon: "✝",
    description: "Patient expired during transit or admission",
    stageIndex: -1,
  },
  CLOSED: {
    label: "Closed",
    badge: "bg-slate-800/40 text-slate-400 border-slate-700/40",
    border: "border-slate-700/40",
    icon: "🔒",
    description: "Administrative record closed",
    stageIndex: -1,
  },
};

export const LIFECYCLE_STAGES = [
  { key: "PENDING", label: "Pending" },
  { key: "ACCEPTED", label: "Accepted" },
  { key: "IN_TRANSIT", label: "In Transit" },
  { key: "ARRIVED", label: "Arrived" },
  { key: "TREATMENT_ACTIVE", label: "Treatment" },
  { key: "COMPLETED", label: "Completed" },
] as const;
