"use client";

import React from "react";
import { Milestone, ApplicationStatus, ApplicationStage } from "@/lib/types";
import { Check, Clock, AlertTriangle, X, FileEdit } from "lucide-react";

interface ApplicationTimelineProps {
  status: ApplicationStatus | string;
  currentStage: ApplicationStage | string;
  milestones?: Milestone[];
  resubmissionVersion?: number;
}

const STAGES_ORDER = [
  { key: "DRAFT", label: "Draft Form" },
  { key: "SUBMITTED", label: "Submission" },
  { key: "DISTRICT_REVIEW", label: "District Review" },
  { key: "STATE_REVIEW", label: "State Review" },
  { key: "CENTRAL_REVIEW", label: "Central Admin" },
  { key: "APPROVED", label: "Approval" },
];

export const ApplicationTimeline: React.FC<ApplicationTimelineProps> = ({
  status,
  currentStage,
  milestones = [],
  resubmissionVersion = 0,
}) => {
  const normStatus = (status || "").toUpperCase();
  const isCorrection = normStatus === "CORRECTION_REQUIRED";
  const isRejected = normStatus === "REJECTED";
  const isApproved = normStatus === "APPROVED" || normStatus === "PROVISIONED";

  const getStatusBadge = () => {
    switch (normStatus) {
      case "APPROVED":
      case "PROVISIONED":
        return {
          bg: "bg-emerald-950/60 border-emerald-500/30 text-emerald-400",
          label: "Approved & Provisioned",
          icon: "✓",
        };
      case "REJECTED":
        return {
          bg: "bg-rose-950/60 border-rose-500/30 text-rose-400",
          label: "Application Rejected",
          icon: "✕",
        };
      case "CORRECTION_REQUIRED":
        return {
          bg: "bg-amber-950/60 border-amber-500/30 text-amber-400",
          label: `Correction Required (v${resubmissionVersion})`,
          icon: "⚠",
        };
      case "SUBMITTED":
      case "UNDER_REVIEW":
        return {
          bg: "bg-teal-950/60 border-teal-500/30 text-teal-400",
          label: "Under Active Review",
          icon: "⟳",
        };
      case "DRAFT":
      default:
        return {
          bg: "bg-slate-800 border-slate-700 text-slate-400",
          label: "Draft - Pending Submission",
          icon: "✎",
        };
    }
  };

  const badge = getStatusBadge();

  return (
    <div className="rounded-2xl border border-slate-800 bg-slate-900/90 backdrop-blur-sm p-5 sm:p-6 shadow-sm">
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-800 pb-4">
        <div>
          <h3 className="text-sm font-bold text-slate-100">Application Verification Progress</h3>
          <p className="text-xs text-slate-400 mt-0.5">
            Current Stage: <span className="text-teal-400 font-semibold">{currentStage.replace(/_/g, " ")}</span>
          </p>
        </div>
        <div
          className={`inline-flex items-center gap-1.5 rounded-full border px-3 py-1 text-xs font-semibold ${badge.bg}`}
        >
          <span>{badge.icon}</span>
          <span>{badge.label}</span>
        </div>
      </div>

      {/* Visual Stepper */}
      <div className="mt-6 hidden sm:grid grid-cols-6 gap-2">
        {STAGES_ORDER.map((stage, idx) => {
          let stepState = "pending"; // completed | current | pending | alert

          if (isApproved) {
            stepState = "completed";
          } else if (isRejected) {
            if (stage.key === currentStage) stepState = "alert";
            else stepState = idx <= 2 ? "completed" : "pending";
          } else if (isCorrection && stage.key === currentStage) {
            stepState = "alert";
          } else if (stage.key === currentStage) {
            stepState = "current";
          } else {
            // Check if stage is earlier
            const currentIdx = STAGES_ORDER.findIndex((s) => s.key === currentStage);
            if (idx < currentIdx) stepState = "completed";
            else stepState = "pending";
          }

          return (
            <div key={stage.key} className="flex flex-col items-center text-center relative">
              <div
                className={`flex h-9 w-9 items-center justify-center rounded-xl text-xs font-bold border transition ${
                  stepState === "completed"
                    ? "bg-emerald-600 border-emerald-600 text-white shadow-sm"
                    : stepState === "current"
                    ? "bg-teal-600 border-teal-600 text-white shadow-md shadow-teal-600/30 ring-4 ring-teal-500/15"
                    : stepState === "alert"
                    ? "bg-amber-600 border-amber-600 text-white shadow-sm"
                    : "bg-slate-950/60 border-slate-800 text-slate-500"
                }`}
              >
                {stepState === "completed" ? (
                  <Check className="w-4 h-4 stroke-[2.5]" />
                ) : stepState === "alert" ? (
                  <AlertTriangle className="w-4 h-4" />
                ) : (
                  idx + 1
                )}
              </div>
              <span
                className={`mt-2 text-[11px] leading-tight font-medium ${
                  stepState === "current"
                    ? "text-teal-400 font-bold"
                    : stepState === "completed"
                    ? "text-emerald-400 font-semibold"
                    : stepState === "alert"
                    ? "text-amber-400 font-semibold"
                    : "text-slate-500"
                }`}
              >
                {stage.label}
              </span>
            </div>
          );
        })}
      </div>

      {/* Milestones Log List */}
      {milestones && milestones.length > 0 && (
        <div className="mt-6 border-t border-slate-800 pt-5">
          <h4 className="text-xs font-bold text-slate-300 uppercase tracking-wider mb-3">
            Milestone Audit History ({milestones.length})
          </h4>
          <div className="space-y-2.5">
            {milestones.map((m, i) => (
              <div
                key={i}
                className="flex items-start gap-3 rounded-xl border border-slate-800 bg-slate-950/60 p-3 text-xs"
              >
                <div className="mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-teal-950 border border-teal-800 text-teal-400 text-[10px] font-bold">
                  ●
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex flex-wrap items-center justify-between gap-1">
                    <span className="font-bold text-slate-100">
                      {m.action ? m.action.replace(/_/g, " ") : m.stage}
                    </span>
                    {m.timestamp && (
                      <span className="text-[11px] text-slate-400 font-mono">
                        {new Date(m.timestamp).toLocaleString()}
                      </span>
                    )}
                  </div>
                  <div className="mt-1 flex items-center gap-2 text-[11px] text-slate-400">
                    <span>Stage: <strong className="text-slate-200">{m.stage}</strong></span>
                    <span>•</span>
                    <span>Status: <strong className="text-slate-200">{m.status}</strong></span>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};
