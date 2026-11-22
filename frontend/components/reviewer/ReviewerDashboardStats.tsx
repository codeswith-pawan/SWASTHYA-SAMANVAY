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
      color: "text-[#0B2345] bg-blue-50 border-blue-200",
      sub: "In reviewer jurisdiction",
    },
    {
      label: "Awaiting Action",
      value: awaitingMyAction,
      icon: Zap,
      color: "text-amber-800 bg-amber-50 border-amber-300",
      sub: `Pending at ${myActionStage.replace(/_/g, " ")}`,
      highlight: true,
    },
    {
      label: "Under Active Review",
      value: pendingCount,
      icon: Clock,
      color: "text-[#008F83] bg-teal-50 border-teal-200",
      sub: "Processing through workflow",
    },
    {
      label: "Correction Required",
      value: correctionCount,
      icon: AlertTriangle,
      color: "text-rose-800 bg-rose-50 border-rose-200",
      sub: "Awaiting applicant resubmission",
    },
    {
      label: "Approved & Cleared",
      value: approvedCount,
      icon: CheckCircle2,
      color: "text-[#0A9878] bg-emerald-50 border-emerald-200",
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
            className={`gov-card p-4 sm:p-5 flex flex-col justify-between transition-all bg-white border ${
              s.highlight
                ? "border-amber-400 ring-2 ring-amber-400/20 shadow-sm"
                : "border-[#DCE5EF]"
            }`}
          >
            <div className="flex items-center justify-between">
              <span className="text-[11px] font-bold uppercase tracking-wider text-[#60738C] leading-tight">
                {s.label}
              </span>
              <div className={`p-2 rounded-xl border ${s.color}`}>
                <Icon className="w-4 h-4" />
              </div>
            </div>

            <div className="mt-3">
              <span className="text-2xl sm:text-3xl font-extrabold text-[#0B2345] tracking-tight">
                {s.value}
              </span>
              <p className="text-[10px] sm:text-[11px] text-[#60738C] mt-1 font-medium truncate">
                {s.sub}
              </p>
            </div>
          </div>
        );
      })}
    </div>
  );
};
