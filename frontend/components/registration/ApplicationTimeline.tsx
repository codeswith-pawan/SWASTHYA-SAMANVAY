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
          bg: "bg-emerald-50 border-emerald-200 text-emerald-700",
          label: "Approved & Provisioned",
          icon: "✓",
        };
      case "REJECTED":
        return {
          bg: "bg-rose-50 border-rose-200 text-rose-700",
          label: "Application Rejected",
          icon: "✕",
        };
      case "CORRECTION_REQUIRED":
        return {
          bg: "bg-amber-50 border-amber-200 text-amber-700",
          label: `Correction Required (v${resubmissionVersion})`,
          icon: "⚠",
        };
      case "SUBMITTED":
      case "UNDER_REVIEW":
        return {
          bg: "bg-indigo-50 border-indigo-200 text-indigo-700",
          label: "Under Active Review",
          icon: "⟳",
        };
      case "DRAFT":
      default:
        return {
          bg: "bg-slate-100 border-slate-200 text-slate-600",
          label: "Draft - Pending Submission",
          icon: "✎",
        };
    }
  };

  const badge = getStatusBadge();

  return (
    <div className="rounded-2xl border border-slate-200/80 bg-white/95 backdrop-blur-sm p-5 sm:p-6 shadow-[0_4px_20px_rgb(15,23,42,0.04)]">
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-100 pb-4">
        <div>
          <h3 className="text-sm font-bold text-slate-900">Application Verification Progress</h3>
          <p className="text-xs text-slate-500 mt-0.5">
            Current Stage: <span className="text-slate-800 font-semibold">{currentStage.replace(/_/g, " ")}</span>
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
                    ? "bg-emerald-500 border-emerald-500 text-white shadow-sm"
                    : stepState === "current"
                    ? "bg-indigo-600 border-indigo-600 text-white shadow-md shadow-indigo-600/30 ring-4 ring-indigo-500/15"
                    : stepState === "alert"
                    ? "bg-amber-500 border-amber-500 text-white shadow-sm"
                    : "bg-slate-100 border-slate-200 text-slate-400"
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
                    ? "text-indigo-700 font-bold"
                    : stepState === "completed"
                    ? "text-emerald-700 font-semibold"
                    : stepState === "alert"
                    ? "text-amber-700 font-semibold"
                    : "text-slate-400"
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
        <div className="mt-6 border-t border-slate-100 pt-5">
          <h4 className="text-xs font-bold text-slate-800 uppercase tracking-wider mb-3">
            Milestone Audit History ({milestones.length})
          </h4>
          <div className="space-y-2.5">
            {milestones.map((m, i) => (
              <div
                key={i}
                className="flex items-start gap-3 rounded-xl border border-slate-200/80 bg-slate-50/70 p-3 text-xs"
              >
                <div className="mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-indigo-50 border border-indigo-200 text-indigo-700 text-[10px] font-bold">
                  ●
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex flex-wrap items-center justify-between gap-1">
                    <span className="font-bold text-slate-800">
                      {m.action ? m.action.replace(/_/g, " ") : m.stage}
                    </span>
                    {m.timestamp && (
                      <span className="text-[11px] text-slate-500 font-mono">
                        {new Date(m.timestamp).toLocaleString()}
                      </span>
                    )}
                  </div>
                  <div className="mt-1 flex items-center gap-2 text-[11px] text-slate-500">
                    <span>Stage: <strong className="text-slate-700">{m.stage}</strong></span>
                    <span>•</span>
                    <span>Status: <strong className="text-slate-700">{m.status}</strong></span>
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
