"use client";

import React from "react";
import { ReviewerApplicationSummary, Role } from "@/lib/types";
import { ClipboardList, Zap, Clock, AlertTriangle, CheckCircle2 } from "lucide-react";

interface ReviewerDashboardStatsProps {
  applications: ReviewerApplicationSummary[];
  totalCount: number;
  role: Role;
}

export const ReviewerDashboardStats: React.FC<ReviewerDashboardStatsProps> = ({
  applications,
  totalCount,
  role,
}) => {
  const myActionStage =
    role === "DISTRICT_ADMIN"
      ? "DISTRICT_REVIEW"
      : role === "STATE_ADMIN"
      ? "STATE_REVIEW"
      : "CENTRAL_REVIEW";

  const pendingCount = applications.filter(
    (a) => a.status === "SUBMITTED" || a.status === "UNDER_REVIEW"
  ).length;

  const awaitingMyAction = applications.filter(
    (a) => a.current_stage === myActionStage && a.status !== "APPROVED" && a.status !== "REJECTED"
  ).length;

  const correctionCount = applications.filter(
    (a) => a.status === "CORRECTION_REQUIRED"
  ).length;

  const approvedCount = applications.filter(
    (a) => a.status === "APPROVED" || a.status === "PROVISIONED"
  ).length;

  const stats = [
    {
      label: "Total Queue Applications",
      value: totalCount,
      icon: ClipboardList,
      color: "text-blue-400 bg-blue-950/40 border-blue-500/30",
      sub: "In reviewer jurisdiction",
    },
    {
      label: "Awaiting Action",
      value: awaitingMyAction,
      icon: Zap,
      color: "text-amber-400 bg-amber-950/40 border-amber-500/30",
      sub: `Pending at ${myActionStage.replace(/_/g, " ")}`,
      highlight: true,
    },
    {
      label: "Under Active Review",
      value: pendingCount,
      icon: Clock,
      color: "text-teal-400 bg-teal-950/40 border-teal-500/30",
      sub: "Processing through workflow",
    },
    {
      label: "Correction Required",
      value: correctionCount,
      icon: AlertTriangle,
      color: "text-rose-400 bg-rose-950/40 border-rose-500/30",
      sub: "Awaiting applicant resubmission",
    },
    {
      label: "Approved & Cleared",
      value: approvedCount,
      icon: CheckCircle2,
      color: "text-emerald-400 bg-emerald-950/40 border-emerald-500/30",
      sub: "Provisioned or forwarded",
    },
  ];

  return (
    <div className="grid grid-cols-2 md:grid-cols-5 gap-3 sm:gap-4">
      {stats.map((s, idx) => {
        const Icon = s.icon;
        return (
          <div
            key={idx}
            className={`rounded-2xl p-4 sm:p-5 flex flex-col justify-between transition-all bg-slate-900/90 border ${
              s.highlight
                ? "border-amber-500/40 ring-1 ring-amber-500/20 shadow-sm"
                : "border-slate-800 shadow-sm"
            }`}
          >
            <div className="flex items-center justify-between">
              <span className="text-[11px] font-bold uppercase tracking-wider text-slate-400 leading-tight">
                {s.label}
              </span>
              <div className={`p-2 rounded-xl border ${s.color}`}>
                <Icon className="w-4 h-4" />
              </div>
            </div>

            <div className="mt-3">
              <span className="text-2xl sm:text-3xl font-extrabold text-slate-100 tracking-tight">
                {s.value}
              </span>
              <p className="text-[10px] sm:text-[11px] text-slate-400 mt-1 font-medium truncate">
                {s.sub}
              </p>
            </div>
          </div>
        );
      })}
    </div>
  );
};
