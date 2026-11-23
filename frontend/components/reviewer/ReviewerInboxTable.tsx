"use client";

import React, { useState } from "react";
import { ReviewerApplicationSummary, Role } from "@/lib/types";
import { formatDateTime } from "@/lib/formatters";
import { Search, RotateCw, ChevronLeft, ChevronRight, FileText, ArrowRight, Inbox } from "lucide-react";

interface ReviewerInboxTableProps {
  applications: ReviewerApplicationSummary[];
  total: number;
  loading: boolean;
  onSelectApplication: (appId: string) => void;
  statusFilter: string;
  onStatusFilterChange: (val: string) => void;
  stageFilter: string;
  onStageFilterChange: (val: string) => void;
  typeFilter: string;
  onTypeFilterChange: (val: string) => void;
  onRefresh: () => void;
  role: Role;
}

export const ReviewerInboxTable: React.FC<ReviewerInboxTableProps> = ({
  applications,
  total,
  loading,
  onSelectApplication,
  statusFilter,
  onStatusFilterChange,
  stageFilter,
  onStageFilterChange,
  typeFilter,
  onTypeFilterChange,
  onRefresh,
  role,
}) => {
  const [searchQuery, setSearchQuery] = useState("");
  const [currentPage, setCurrentPage] = useState(1);
  const pageSize = 10;

  // Client-side search refinement on loaded batch
  const filtered = applications.filter((app) => {
    if (!searchQuery.trim()) return true;
    const q = searchQuery.toLowerCase();
    return (
      app.application_number.toLowerCase().includes(q) ||
      app.applicant_name.toLowerCase().includes(q) ||
      app.applicant_email.toLowerCase().includes(q) ||
      (app.district && app.district.toLowerCase().includes(q)) ||
      app.state.toLowerCase().includes(q)
    );
  });

  const totalPages = Math.max(1, Math.ceil(filtered.length / pageSize));
  const pagedApps = filtered.slice((currentPage - 1) * pageSize, currentPage * pageSize);

  const getStatusBadge = (status: string) => {
    switch (status) {
      case "APPROVED":
      case "PROVISIONED":
        return "bg-emerald-950/60 text-emerald-400 border-emerald-500/30";
      case "REJECTED":
        return "bg-rose-950/60 text-rose-400 border-rose-500/30";
      case "CORRECTION_REQUIRED":
        return "bg-amber-950/60 text-amber-400 border-amber-500/30";
      case "SUBMITTED":
      case "UNDER_REVIEW":
        return "bg-teal-950/60 text-teal-400 border-teal-500/30";
      case "DRAFT":
      default:
        return "bg-slate-800 text-slate-400 border-slate-700";
    }
  };

  const getTypeBadge = (type: string) => {
    switch (type) {
      case "HOSPITAL":
        return "bg-teal-950/60 text-teal-400 border-teal-500/30";
      case "DISTRICT":
        return "bg-blue-950/60 text-blue-400 border-blue-500/30";
      case "STATE":
        return "bg-cyan-950/60 text-cyan-400 border-cyan-500/30";
      default:
        return "bg-slate-800 text-slate-400 border-slate-700";
    }
  };

  return (
    <div className="rounded-2xl border border-slate-800 bg-slate-900/90 overflow-hidden shadow-sm">
      {/* Top Controls Bar */}
      <div className="p-4 sm:p-5 border-b border-slate-800 flex flex-col md:flex-row items-stretch md:items-center justify-between gap-4 bg-slate-900/60">
        {/* Search */}
        <div className="relative flex-1 max-w-md">
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => {
              setSearchQuery(e.target.value);
              setCurrentPage(1);
            }}
            placeholder="Search by application #, name, or jurisdiction..."
            className="w-full rounded-xl border border-slate-700 bg-slate-950/80 px-3.5 py-2 pl-9 text-xs text-slate-100 placeholder-slate-500 outline-none focus:border-teal-500 focus:ring-2 focus:ring-teal-500/20 transition"
          />
          <Search className="w-4 h-4 text-slate-500 absolute left-3 top-2.5" />
        </div>

        {/* Filters */}
        <div className="flex flex-wrap items-center gap-2.5">
          <select
            value={statusFilter}
            onChange={(e) => {
              onStatusFilterChange(e.target.value);
              setCurrentPage(1);
            }}
            className="rounded-xl border border-slate-700 bg-slate-950/80 px-3 py-2 text-xs text-slate-200 outline-none focus:border-teal-500 transition"
          >
            <option value="">All Statuses</option>
            <option value="SUBMITTED">Submitted</option>
            <option value="UNDER_REVIEW">Under Review</option>
            <option value="CORRECTION_REQUIRED">Correction Required</option>
            <option value="APPROVED">Approved</option>
            <option value="REJECTED">Rejected</option>
          </select>

          <select
            value={stageFilter}
            onChange={(e) => {
              onStageFilterChange(e.target.value);
              setCurrentPage(1);
            }}
            className="rounded-xl border border-slate-700 bg-slate-950/80 px-3 py-2 text-xs text-slate-200 outline-none focus:border-teal-500 transition"
          >
            <option value="">All Stages</option>
            <option value="DISTRICT_REVIEW">District Review</option>
            <option value="STATE_REVIEW">State Review</option>
            <option value="CENTRAL_REVIEW">Central Review</option>
          </select>

          <select
            value={typeFilter}
            onChange={(e) => {
              onTypeFilterChange(e.target.value);
              setCurrentPage(1);
            }}
            className="rounded-xl border border-slate-700 bg-slate-950/80 px-3 py-2 text-xs text-slate-200 outline-none focus:border-teal-500 transition"
          >
            <option value="">All Types</option>
            <option value="HOSPITAL">Hospital</option>
            <option value="DISTRICT">District</option>
            <option value="STATE">State</option>
          </select>

          <button
            onClick={onRefresh}
            disabled={loading}
            className="inline-flex items-center gap-1.5 rounded-xl border border-slate-700 bg-slate-800/80 px-3.5 py-2 text-xs font-semibold text-slate-200 hover:bg-slate-700 hover:text-white transition disabled:opacity-50"
            title="Refresh application queue"
          >
            <RotateCw className={`w-3.5 h-3.5 ${loading ? "animate-spin text-teal-400" : ""}`} />
            <span>Refresh</span>
          </button>
        </div>
      </div>

      {/* Table Area */}
      <div className="overflow-x-auto">
        <table className="w-full text-left text-xs border-collapse">
          <thead>
            <tr className="border-b border-slate-800 bg-slate-950/60 text-[11px] font-bold text-slate-400 uppercase tracking-wider">
              <th className="py-3.5 px-4">Application #</th>
              <th className="py-3.5 px-4">Applicant / Institution</th>
              <th className="py-3.5 px-4">Tier</th>
              <th className="py-3.5 px-4">Jurisdiction</th>
              <th className="py-3.5 px-4">Status</th>
              <th className="py-3.5 px-4">Current Stage</th>
              <th className="py-3.5 px-4 text-center">Docs</th>
              <th className="py-3.5 px-4">Submitted</th>
              <th className="py-3.5 px-4 text-right">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-800/80">
            {loading ? (
              <tr>
                <td colSpan={9} className="py-12 text-center text-slate-400">
                  <div className="flex flex-col items-center justify-center gap-2">
                    <span className="h-5 w-5 animate-spin rounded-full border-2 border-teal-400 border-t-transparent" />
                    <span className="font-medium text-xs">Loading reviewer queue...</span>
                  </div>
                </td>
              </tr>
            ) : pagedApps.length === 0 ? (
              <tr>
                <td colSpan={9} className="py-12 text-center text-slate-400">
                  <div className="flex flex-col items-center justify-center gap-2">
                    <Inbox className="w-8 h-8 text-slate-600" />
                    <span className="font-bold text-slate-200">No applications match the selected criteria.</span>
                    <p className="text-[11px] text-slate-400 max-w-sm">
                      Check your filters or refresh the queue to view newly submitted applications in your jurisdiction.
                    </p>
                  </div>
                </td>
              </tr>
            ) : (
              pagedApps.map((app) => (
                <tr
                  key={app.application_id}
                  className="hover:bg-slate-800/50 transition group cursor-pointer"
                  onClick={() => onSelectApplication(app.application_id)}
                >
                  <td className="py-3.5 px-4 font-mono font-bold text-teal-400">
                    {app.application_number}
                    {app.resubmission_version > 1 && (
                      <span className="ml-1 text-[10px] text-amber-400 font-normal">
                        (v{app.resubmission_version})
                      </span>
                    )}
                  </td>
                  <td className="py-3.5 px-4">
                    <p className="font-bold text-slate-100 group-hover:text-teal-300 transition">
                      {app.applicant_name}
                    </p>
                    <p className="text-[11px] text-slate-400 truncate max-w-xs">{app.applicant_email}</p>
                  </td>
                  <td className="py-3.5 px-4">
                    <span
                      className={`inline-flex rounded-full border px-2.5 py-0.5 text-[10px] font-bold ${getTypeBadge(
                        app.applicant_type
                      )}`}
                    >
                      {app.applicant_type}
                    </span>
                  </td>
                  <td className="py-3.5 px-4 text-slate-300">
                    {app.district ? `${app.district}, ` : ""}
                    <strong className="text-slate-100 font-semibold">{app.state}</strong>
                  </td>
                  <td className="py-3.5 px-4">
                    <span
                      className={`inline-flex items-center gap-1 rounded-full border px-2.5 py-0.5 text-[10px] font-bold ${getStatusBadge(
                        app.status
                      )}`}
                    >
                      {app.status.replace(/_/g, " ")}
                    </span>
                  </td>
                  <td className="py-3.5 px-4 font-semibold text-slate-300">
                    {app.current_stage.replace(/_/g, " ")}
                  </td>
                  <td className="py-3.5 px-4 text-center">
                    <span
                      className={`font-bold ${
                        app.pending_documents_count > 0 ? "text-amber-400" : "text-emerald-400"
                      }`}
                    >
                      {Math.max(0, app.documents_count - app.pending_documents_count)}/{app.documents_count}
                    </span>
                  </td>
                  <td className="py-3.5 px-4 text-slate-400 font-mono text-[11px]">
                    {app.submitted_at ? formatDateTime(app.submitted_at) : "Draft"}
                  </td>
                  <td className="py-3.5 px-4 text-right">
                    <button
                      type="button"
                      onClick={(e) => {
                        e.stopPropagation();
                        onSelectApplication(app.application_id);
                      }}
                      className="inline-flex items-center gap-1 rounded-lg bg-teal-950/60 border border-teal-500/30 px-3 py-1.5 text-xs font-bold text-teal-300 hover:bg-teal-600 hover:text-white transition shadow-2xs"
                    >
                      <span>Inspect Dossier</span>
                      <ArrowRight className="w-3.5 h-3.5" />
                    </button>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {/* Pagination Footer */}
      {totalPages > 1 && (
        <div className="p-4 border-t border-slate-800 flex items-center justify-between text-xs text-slate-400 bg-slate-950/60">
          <span>
            Showing page <strong className="text-slate-200">{currentPage}</strong> of{" "}
            <strong className="text-slate-200">{totalPages}</strong> ({filtered.length} total)
          </span>

          <div className="flex items-center gap-2">
            <button
              onClick={() => setCurrentPage((p) => Math.max(1, p - 1))}
              disabled={currentPage === 1}
              className="p-1.5 rounded-lg border border-slate-700 text-slate-300 hover:bg-slate-800 disabled:opacity-40 transition"
              aria-label="Previous page"
            >
              <ChevronLeft className="w-4 h-4" />
            </button>
            <span className="font-mono text-xs font-semibold px-2 text-slate-200">{currentPage}</span>
            <button
              onClick={() => setCurrentPage((p) => Math.min(totalPages, p + 1))}
              disabled={currentPage === totalPages}
              className="p-1.5 rounded-lg border border-slate-700 text-slate-300 hover:bg-slate-800 disabled:opacity-40 transition"
              aria-label="Next page"
            >
              <ChevronRight className="w-4 h-4" />
            </button>
          </div>
        </div>
      )}
    </div>
  );
};
