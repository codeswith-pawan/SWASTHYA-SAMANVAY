"use client";

import React, { useState } from "react";
import { ReviewerApplicationDetail, Role, ReviewDecisionPayload } from "@/lib/types";
import {
  apiVerifyReviewerDocument,
  apiExecuteReviewDecision,
  apiReviewerRequestCorrection,
  apiDownloadDocumentBlob,
} from "@/lib/api";
import { ApplicationTimeline } from "@/components/registration/ApplicationTimeline";
import { formatDateTime } from "@/lib/formatters";
import {
  ArrowLeft,
  FileText,
  CheckCircle2,
  XCircle,
  AlertTriangle,
  Download,
  Eye,
  ShieldCheck,
  Building,
  User,
  MapPin,
  Clock,
  ArrowRight,
  Send,
  X,
  Check,
} from "lucide-react";

interface ReviewerDossierViewProps {
  application: ReviewerApplicationDetail;
  role: Role;
  onBack: () => void;
  onApplicationUpdated: () => void;
}

export const ReviewerDossierView: React.FC<ReviewerDossierViewProps> = ({
  application,
  role,
  onBack,
  onApplicationUpdated,
}) => {
  // Action Modals State
  const [activeModal, setActiveModal] = useState<
    "FORWARD" | "APPROVE" | "REJECT" | "CORRECTION" | "DOC_REJECT" | "DOC_PREVIEW" | null
  >(null);

  // Selected document for rejection / preview
  const [selectedDocId, setSelectedDocId] = useState<string | null>(null);
  const [docRejectRemarks, setDocRejectRemarks] = useState("");
  const [previewBlobUrl, setPreviewBlobUrl] = useState<string | null>(null);
  const [previewFilename, setPreviewFilename] = useState("");
  const [previewContentType, setPreviewContentType] = useState("");

  // Decision inputs
  const [decisionRemarks, setDecisionRemarks] = useState("");
  const [correctionNotes, setCorrectionNotes] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [actionSuccess, setActionSuccess] = useState("");

  const formatBytes = (bytes: number) => {
    if (bytes === 0) return "0 Bytes";
    const k = 1024;
    const sizes = ["Bytes", "KB", "MB"];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + " " + sizes[i];
  };

  // Determine permitted decision actions based on role and stage
  const isDistrictReviewer = role === "DISTRICT_ADMIN";
  const isStateReviewer = role === "STATE_ADMIN";
  const isCentralReviewer = role === "CENTRAL_ADMIN";

  const isCurrentStageDistrict = application.current_stage === "DISTRICT_REVIEW";
  const isCurrentStageState = application.current_stage === "STATE_REVIEW";
  const isCurrentStageCentral = application.current_stage === "CENTRAL_REVIEW";

  const canActOnCurrentStage =
    (isDistrictReviewer && isCurrentStageDistrict) ||
    (isStateReviewer && isCurrentStageState) ||
    (isCentralReviewer && isCurrentStageCentral);

  const isTerminal = application.status === "APPROVED" || application.status === "REJECTED";

  // Check if all documents are verified
  const allDocumentsVerified =
    application.documents.length > 0 &&
    application.documents.every((d) => d.verification_status === "VERIFIED");

  // Document Verification Handlers
  const handleVerifyDocument = async (docId: string) => {
    setLoading(true);
    setError("");
    setActionSuccess("");

    try {
      await apiVerifyReviewerDocument(docId, { verification_status: "VERIFIED" });
      setActionSuccess("Document marked as verified.");
      onApplicationUpdated();
    } catch (err: any) {
      setError(err.message || "Failed to verify document.");
    } finally {
      setLoading(false);
    }
  };

  const handleOpenDocRejectModal = (docId: string) => {
    setSelectedDocId(docId);
    setDocRejectRemarks("");
    setActiveModal("DOC_REJECT");
  };

  const handleConfirmDocReject = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedDocId || !docRejectRemarks.trim()) {
      setError("Please provide a reason for rejecting this document.");
      return;
    }

    setLoading(true);
    setError("");

    try {
      await apiVerifyReviewerDocument(selectedDocId, {
        verification_status: "REJECTED",
        reviewer_remarks: docRejectRemarks.trim(),
      });
      setActiveModal(null);
      setSelectedDocId(null);
      setDocRejectRemarks("");
      setActionSuccess("Document marked as rejected with comments.");
      onApplicationUpdated();
    } catch (err: any) {
      setError(err.message || "Failed to reject document.");
    } finally {
      setLoading(false);
    }
  };

  // Document Preview Handler
  const handlePreviewDocument = async (docId: string) => {
    setLoading(true);
    setError("");

    try {
      const { blob, filename, contentType } = await apiDownloadDocumentBlob(docId);
      const url = URL.createObjectURL(blob);
      setPreviewBlobUrl(url);
      setPreviewFilename(filename);
      setPreviewContentType(contentType);
      setActiveModal("DOC_PREVIEW");
    } catch (err: any) {
      setError(err.message || "Failed to load document preview.");
    } finally {
      setLoading(false);
    }
  };

  // Review Decision Handlers
  const handleExecuteDecision = async (action: "FORWARD" | "APPROVE" | "REJECT") => {
    setLoading(true);
    setError("");
    setActionSuccess("");

    try {
      const payload: ReviewDecisionPayload = {
        action,
        remarks: decisionRemarks.trim() || undefined,
      };

      const res = await apiExecuteReviewDecision(application.application_id, payload);
      setActiveModal(null);
      setDecisionRemarks("");
      setActionSuccess(
        `Decision '${action}' executed successfully. Application transitioned to ${res.new_stage.replace(
          /_/g,
          " "
        )} (${res.new_status}).`
      );
      onApplicationUpdated();
    } catch (err: any) {
      setError(err.message || "Failed to execute decision.");
    } finally {
      setLoading(false);
    }
  };

  // Request Correction Handler
  const handleExecuteCorrection = async (e: React.FormEvent) => {
    e.preventDefault();
    if (correctionNotes.trim().length < 5) {
      setError("Please provide specific correction instructions (minimum 5 characters).");
      return;
    }

    setLoading(true);
    setError("");

    try {
      await apiReviewerRequestCorrection(application.application_id, {
        correction_notes: correctionNotes.trim(),
      });
      setActiveModal(null);
      setCorrectionNotes("");
      setActionSuccess("Correction request dispatched to applicant. Status set to CORRECTION_REQUIRED.");
      onApplicationUpdated();
    } catch (err: any) {
      setError(err.message || "Failed to submit correction request.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Top Breadcrumb & Navigation */}
      <div className="flex flex-wrap items-center justify-between gap-4">
        <button
          onClick={onBack}
          className="inline-flex items-center gap-2 rounded-xl border border-slate-800 bg-slate-900 px-4 py-2 text-xs font-bold text-slate-200 hover:bg-slate-800 transition shadow-xs"
        >
          <ArrowLeft className="w-4 h-4 text-teal-400" />
          <span>Back to Application Queue</span>
        </button>

        <div className="flex items-center gap-2 bg-slate-900 px-4 py-2 rounded-xl border border-slate-800 shadow-xs">
          <span className="font-mono text-xs text-slate-400">Dossier:</span>
          <span className="rounded-lg bg-teal-950/60 border border-teal-500/30 px-3 py-0.5 font-mono text-xs font-bold text-teal-300">
            {application.application_number}
          </span>
        </div>
      </div>

      {/* Global Alerts */}
      {error && (
        <div className="rounded-2xl border border-rose-500/30 bg-rose-950/50 p-4 text-xs sm:text-sm text-rose-300 flex items-start gap-3 shadow-xs animate-fade-in-up">
          <AlertTriangle className="w-5 h-5 text-rose-400 shrink-0 mt-0.5" />
          <div className="flex-1 font-medium">{error}</div>
        </div>
      )}

      {actionSuccess && (
        <div className="rounded-2xl border border-emerald-500/30 bg-emerald-950/50 p-4 text-xs sm:text-sm text-emerald-300 flex items-start gap-3 shadow-xs animate-fade-in-up">
          <CheckCircle2 className="w-5 h-5 text-emerald-400 shrink-0 mt-0.5" />
          <div className="flex-1 font-medium">{actionSuccess}</div>
        </div>
      )}

      {/* Dossier Header Overview Card */}
      <div className="rounded-2xl p-6 sm:p-7 bg-slate-900/90 border border-slate-800 shadow-sm space-y-6 text-slate-100">
        <div className="flex flex-wrap items-center justify-between gap-4 border-b border-slate-800 pb-4">
          <div>
            <div className="flex items-center gap-2">
              <span className="rounded-full bg-teal-950/60 border border-teal-500/30 px-3 py-0.5 text-[10px] font-bold text-teal-300 uppercase tracking-wider">
                {application.applicant_type} Facility Dossier
              </span>
              {application.resubmission_version > 1 && (
                <span className="rounded-full bg-amber-950/60 border border-amber-500/30 px-2 py-0.5 text-[10px] font-bold text-amber-400">
                  Version {application.resubmission_version}
                </span>
              )}
            </div>
            <h1 className="mt-2 text-2xl font-extrabold text-slate-100">
              {application.applicant_name}
            </h1>
            <p className="text-xs text-slate-400 mt-0.5">
              Territorial Jurisdiction: {application.district ? `${application.district}, ` : ""}
              <strong className="text-slate-200">{application.state}</strong>
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-2">
            <span
              className={`rounded-full border px-3 py-1 text-xs font-bold ${
                application.status === "APPROVED" || application.status === "PROVISIONED"
                  ? "bg-emerald-950/60 text-emerald-400 border-emerald-500/30"
                  : application.status === "REJECTED"
                  ? "bg-rose-950/60 text-rose-400 border-rose-500/30"
                  : application.status === "CORRECTION_REQUIRED"
                  ? "bg-amber-950/60 text-amber-400 border-amber-500/30"
                  : "bg-teal-950/60 text-teal-400 border-teal-500/30"
              }`}
            >
              Status: {application.status.replace(/_/g, " ")}
            </span>

            <span className="rounded-full border border-slate-800 bg-slate-950/80 px-3 py-1 text-xs font-semibold text-slate-300">
              Stage: {application.current_stage.replace(/_/g, " ")}
            </span>
          </div>
        </div>

        {/* Institution & Contact Grid */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-xs">
          {/* Box 1: Nodal Authority */}
          <div className="rounded-xl border border-slate-800 bg-slate-950/60 p-4 space-y-2">
            <h3 className="font-bold text-slate-200 uppercase tracking-wider text-[11px] flex items-center gap-1.5">
              <User className="w-3.5 h-3.5 text-teal-400" /> Designated Nodal Contact
            </h3>
            <p className="text-slate-400">Officer: <strong className="text-slate-100">{application.nodal_officer_name || "N/A"}</strong></p>
            <p className="text-slate-400">Designation: <strong className="text-slate-100">{application.official_designation || "N/A"}</strong></p>
            <p className="text-slate-400">Official Email: <strong className="text-slate-100">{application.applicant_email}</strong></p>
            <p className="text-slate-400">Official Phone: <strong className="text-slate-100">{application.applicant_phone}</strong></p>
          </div>

          {/* Box 2: Facility Address & Location */}
          <div className="rounded-xl border border-slate-800 bg-slate-950/60 p-4 space-y-2">
            <h3 className="font-bold text-slate-200 uppercase tracking-wider text-[11px] flex items-center gap-1.5">
              <MapPin className="w-3.5 h-3.5 text-teal-400" /> Secretariat / Facility Address
            </h3>
            <p className="text-slate-400">City / Town: <strong className="text-slate-100">{application.city || "N/A"}</strong></p>
            <p className="text-slate-400">Street Address: <strong className="text-slate-100">{application.address || "N/A"}</strong></p>
            <p className="text-slate-400">PIN Code: <strong className="text-slate-100">{application.pincode || "N/A"}</strong></p>
            <p className="text-slate-400">Registered: <strong className="text-slate-100 font-mono">{formatDateTime(application.created_at)}</strong></p>
          </div>

          {/* Box 3: Operational Capacities (if Hospital) */}
          <div className="rounded-xl border border-slate-800 bg-slate-950/60 p-4 space-y-2">
            <h3 className="font-bold text-slate-200 uppercase tracking-wider text-[11px] flex items-center gap-1.5">
              <Building className="w-3.5 h-3.5 text-teal-400" /> Operational Profile & Capacities
            </h3>
            {application.profile_data ? (
              <>
                <p className="text-slate-400">
                  Total Beds: <strong className="text-slate-100">{String(application.profile_data.total_beds || "N/A")}</strong>
                </p>
                <p className="text-slate-400">
                  ICU Capacity: <strong className="text-slate-100">{String(application.profile_data.icu_beds || "N/A")}</strong>
                </p>
                <p className="text-slate-400">
                  Emergency Beds: <strong className="text-slate-100">{String(application.profile_data.emergency_beds || "N/A")}</strong>
                </p>
                <p className="text-slate-400">
                  24x7 Casualty: <strong className="text-emerald-400">{application.profile_data.emergency_24x7 ? "Yes" : "No"}</strong>
                </p>
              </>
            ) : (
              <p className="text-slate-400 italic">Administrative Government Jurisdiction</p>
            )}
          </div>
        </div>

        {/* Existing Rejection / Correction Notes */}
        {application.correction_notes && (
          <div className="rounded-xl border border-amber-500/30 bg-amber-950/50 p-4 text-xs space-y-1">
            <span className="font-bold text-amber-300 flex items-center gap-1.5">
              <AlertTriangle className="w-4 h-4 text-amber-400" /> Active Reviewer Correction Notice:
            </span>
            <p className="text-amber-200 font-mono mt-1">{application.correction_notes}</p>
          </div>
        )}

        {application.rejection_reason && (
          <div className="rounded-xl border border-rose-500/30 bg-rose-950/50 p-4 text-xs space-y-1">
            <span className="font-bold text-rose-300 flex items-center gap-1.5">
              <XCircle className="w-4 h-4 text-rose-400" /> Final Rejection Reason:
            </span>
            <p className="text-rose-200 font-mono mt-1">{application.rejection_reason}</p>
          </div>
        )}
      </div>

      {/* Document Verification Checklist Section */}
      <div className="rounded-2xl p-6 sm:p-7 bg-slate-900/90 border border-slate-800 shadow-sm space-y-5 text-slate-100">
        <div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-800 pb-4">
          <div>
            <h2 className="text-base font-bold text-slate-100">Regulatory Document Verification Checklist</h2>
            <p className="text-xs text-slate-400 mt-0.5">
              Examine each uploaded document scan and mark as verified or rejected with mandatory comments.
            </p>
          </div>

          <div className="flex items-center gap-2 text-xs">
            <span className="text-slate-400">Verification Progress:</span>
            <span
              className={`font-bold font-mono px-3 py-0.5 rounded-full border ${
                allDocumentsVerified
                  ? "bg-emerald-950/60 text-emerald-400 border-emerald-500/30"
                  : "bg-amber-950/60 text-amber-400 border-amber-500/30"
              }`}
            >
              {application.documents.filter((d) => d.verification_status === "VERIFIED").length} /{" "}
              {application.documents.length} Verified
            </span>
          </div>
        </div>

        {/* Document Cards List */}
        <div className="space-y-3">
          {application.documents.map((doc) => (
            <div
              key={doc.document_id}
              className={`rounded-xl border p-4 transition ${
                doc.verification_status === "VERIFIED"
                  ? "border-emerald-500/30 bg-emerald-950/20"
                  : doc.verification_status === "REJECTED"
                  ? "border-rose-500/30 bg-rose-950/20"
                  : "border-slate-800 bg-slate-950/60"
              }`}
            >
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                <div className="flex items-start gap-3 min-w-0">
                  <div className="p-2 rounded-lg bg-slate-900 border border-slate-700 text-teal-400 shrink-0">
                    <FileText className="w-5 h-5" />
                  </div>
                  <div className="min-w-0">
                    <div className="flex items-center gap-2">
                      <span className="text-xs font-bold text-slate-100">{doc.document_type}</span>
                      <span
                        className={`rounded-full border px-2.5 py-0.5 text-[10px] font-bold ${
                          doc.verification_status === "VERIFIED"
                            ? "bg-emerald-950/60 text-emerald-400 border-emerald-500/30"
                            : doc.verification_status === "REJECTED"
                            ? "bg-rose-950/60 text-rose-400 border-rose-500/30"
                            : "bg-teal-950/60 text-teal-400 border-teal-500/30"
                        }`}
                      >
                        {doc.verification_status}
                      </span>
                    </div>
                    <p className="text-xs text-slate-300 font-medium truncate mt-0.5">
                      {doc.original_filename}
                    </p>
                    <p className="text-[11px] text-slate-400 font-mono">
                      {formatBytes(doc.file_size_bytes)} &bull; Uploaded {formatDateTime(doc.uploaded_at)}
                    </p>
                  </div>
                </div>

                {/* Document Actions */}
                <div className="flex items-center gap-2 shrink-0">
                  <button
                    type="button"
                    onClick={() => handlePreviewDocument(doc.document_id)}
                    disabled={loading}
                    className="inline-flex items-center gap-1.5 rounded-lg border border-slate-700 bg-slate-800 px-3 py-1.5 text-xs font-bold text-slate-200 hover:bg-slate-700 transition shadow-2xs"
                  >
                    <Eye className="w-3.5 h-3.5 text-teal-400" />
                    <span>Inspect File</span>
                  </button>

                  {canActOnCurrentStage && !isTerminal && (
                    <>
                      <button
                        type="button"
                        onClick={() => handleVerifyDocument(doc.document_id)}
                        disabled={loading || doc.verification_status === "VERIFIED"}
                        className="inline-flex items-center gap-1 rounded-lg border border-emerald-500/30 bg-emerald-950/60 px-3 py-1.5 text-xs font-bold text-emerald-300 hover:bg-emerald-600 hover:text-white disabled:opacity-40 transition shadow-2xs"
                      >
                        <Check className="w-3.5 h-3.5" />
                        <span>Verify</span>
                      </button>

                      <button
                        type="button"
                        onClick={() => handleOpenDocRejectModal(doc.document_id)}
                        disabled={loading}
                        className="inline-flex items-center gap-1 rounded-lg border border-rose-500/30 bg-rose-950/60 px-3 py-1.5 text-xs font-bold text-rose-300 hover:bg-rose-600 hover:text-white disabled:opacity-40 transition shadow-2xs"
                      >
                        <X className="w-3.5 h-3.5" />
                        <span>Reject</span>
                      </button>
                    </>
                  )}
                </div>
              </div>

              {/* Reviewer remarks if rejected */}
              {doc.reviewer_remarks && (
                <div className="mt-3 rounded-lg border border-rose-500/30 bg-rose-950/60 p-2.5 text-xs text-rose-200 font-mono">
                  <strong className="font-sans font-bold">Reviewer Rejection Reason:</strong> {doc.reviewer_remarks}
                </div>
              )}
            </div>
          ))}
        </div>
      </div>

      {/* Reviewer Stage Decision Bar */}
      {canActOnCurrentStage && !isTerminal && (
        <div className="rounded-2xl p-6 sm:p-7 bg-slate-900/90 border border-teal-500/30 shadow-md space-y-4 text-slate-100">
          <div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-800 pb-4">
            <div>
              <span className="rounded-full bg-teal-950/60 border border-teal-500/30 px-3 py-0.5 text-[10px] font-bold text-teal-300 uppercase tracking-wider">
                Jurisdiction Decision Authority
              </span>
              <h2 className="mt-1.5 text-base font-bold text-slate-100">
                Execute Review Decision on Application
              </h2>
              <p className="text-xs text-slate-400">
                You are reviewing as <strong className="text-slate-200">{role.replace(/_/g, " ")}</strong> at stage{" "}
                <strong className="text-teal-400">{application.current_stage.replace(/_/g, " ")}</strong>.
              </p>
            </div>

            {/* Checklist requirement */}
            <div className="text-xs">
              {!allDocumentsVerified ? (
                <span className="inline-flex items-center gap-1.5 rounded-full border border-amber-500/30 bg-amber-950/60 px-3 py-1 font-semibold text-amber-300">
                  <AlertTriangle className="w-3.5 h-3.5" />
                  All documents must be marked Verified before forwarding/approval
                </span>
              ) : (
                <span className="inline-flex items-center gap-1.5 rounded-full border border-emerald-500/30 bg-emerald-950/60 px-3 py-1 font-semibold text-emerald-300">
                  <CheckCircle2 className="w-3.5 h-3.5" />
                  Document checklist complete
                </span>
              )}
            </div>
          </div>

          {/* Action Buttons */}
          <div className="flex flex-wrap items-center justify-end gap-3 pt-2">
            <button
              type="button"
              onClick={() => {
                setCorrectionNotes("");
                setActiveModal("CORRECTION");
              }}
              className="inline-flex items-center gap-1.5 rounded-xl border border-amber-500/30 bg-amber-950/60 px-4 py-2.5 text-xs font-bold text-amber-300 hover:bg-amber-900/60 transition shadow-xs"
            >
              <AlertTriangle className="w-3.5 h-3.5" />
              <span>Request Applicant Correction</span>
            </button>

            <button
              type="button"
              onClick={() => {
                setDecisionRemarks("");
                setActiveModal("REJECT");
              }}
              className="inline-flex items-center gap-1.5 rounded-xl border border-rose-500/30 bg-rose-950/60 px-4 py-2.5 text-xs font-bold text-rose-300 hover:bg-rose-900/60 transition shadow-xs"
            >
              <XCircle className="w-3.5 h-3.5" />
              <span>Reject Application</span>
            </button>

            {isCentralReviewer ? (
              <button
                type="button"
                disabled={!allDocumentsVerified}
                onClick={() => {
                  setDecisionRemarks("");
                  setActiveModal("APPROVE");
                }}
                className="inline-flex items-center gap-1.5 rounded-xl bg-gradient-to-r from-emerald-600 to-teal-600 px-6 py-2.5 text-xs font-bold text-white hover:from-emerald-500 hover:to-teal-500 disabled:opacity-40 transition shadow-md shadow-emerald-600/20"
              >
                <CheckCircle2 className="w-4 h-4" />
                <span>Final Approve & Provision Account</span>
              </button>
            ) : (
              <button
                type="button"
                disabled={!allDocumentsVerified}
                onClick={() => {
                  setDecisionRemarks("");
                  setActiveModal("FORWARD");
                }}
                className="inline-flex items-center gap-1.5 rounded-xl bg-gradient-to-r from-teal-600 to-teal-500 px-6 py-2.5 text-xs font-bold text-white hover:from-teal-500 hover:to-teal-400 disabled:opacity-40 transition shadow-md shadow-teal-600/20"
              >
                <span>Forward to Next Review Authority</span>
                <ArrowRight className="w-4 h-4" />
              </button>
            )}
          </div>
        </div>
      )}

      {/* Application Timeline & Milestone Progression */}
      <ApplicationTimeline
        status={application.status}
        currentStage={application.current_stage}
        resubmissionVersion={application.resubmission_version}
      />

      {/* Reviewer Audit History Table */}
      {application.history && application.history.length > 0 && (
        <div className="rounded-2xl p-6 sm:p-7 bg-slate-900/90 border border-slate-800 shadow-sm space-y-4 text-slate-100">
          <h2 className="text-xs font-bold text-slate-300 uppercase tracking-wider">
            Reviewer Decision Audit Trail ({application.history.length})
          </h2>

          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs border-collapse">
              <thead>
                <tr className="border-b border-slate-800 bg-slate-950/60 text-[11px] font-bold text-slate-400 uppercase">
                  <th className="py-2.5 px-3">Action</th>
                  <th className="py-2.5 px-3">Review Tier</th>
                  <th className="py-2.5 px-3">Reviewer ID</th>
                  <th className="py-2.5 px-3">Transition</th>
                  <th className="py-2.5 px-3">Remarks</th>
                  <th className="py-2.5 px-3">Timestamp</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/80">
                {application.history.map((h, i) => (
                  <tr key={i} className="hover:bg-slate-800/50 transition">
                    <td className="py-2.5 px-3 font-bold text-teal-400">{h.action}</td>
                    <td className="py-2.5 px-3 text-slate-200">{h.review_tier}</td>
                    <td className="py-2.5 px-3 font-mono text-slate-400">{h.reviewer_user_id}</td>
                    <td className="py-2.5 px-3 text-slate-400">
                      {h.previous_status} &rarr; <strong className="text-slate-100">{h.new_status}</strong>
                    </td>
                    <td className="py-2.5 px-3 text-slate-300 max-w-xs truncate">{h.remarks || "—"}</td>
                    <td className="py-2.5 px-3 font-mono text-slate-400 text-[11px]">
                      {h.created_at ? formatDateTime(h.created_at) : "N/A"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* ============================================================ */}
      {/* ACTION CONFIRMATION MODALS                                  */}
      {/* ============================================================ */}

      {/* FORWARD CONFIRMATION MODAL */}
      {activeModal === "FORWARD" && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/75 backdrop-blur-md p-4 animate-fade-in-up">
          <div className="w-full max-w-md rounded-2xl border border-slate-800 bg-slate-900 p-6 space-y-4 shadow-2xl text-slate-100">
            <h3 className="text-base font-bold text-slate-100">Forward Application to Next Review Level</h3>
            <p className="text-xs text-slate-400">
              Confirm forwarding application <strong className="text-teal-400">{application.application_number}</strong> to the higher authority tier.
            </p>
            <div>
              <label className="block text-xs font-semibold text-slate-300 mb-1">Reviewer Endorsement Remarks (Optional)</label>
              <textarea
                rows={3}
                value={decisionRemarks}
                onChange={(e) => setDecisionRemarks(e.target.value)}
                placeholder="e.g. All clinical licenses and fire safety NOCs verified on site."
                className="w-full rounded-xl border border-slate-700 bg-slate-950 p-3 text-xs text-slate-100 placeholder-slate-500 outline-none focus:border-teal-500 focus:ring-2 focus:ring-teal-500/20 transition"
              />
            </div>
            <div className="flex justify-end gap-3 pt-2">
              <button
                type="button"
                onClick={() => setActiveModal(null)}
                className="rounded-xl border border-slate-700 bg-slate-800 px-4 py-2 text-xs font-bold text-slate-300 hover:bg-slate-700 transition"
              >
                Cancel
              </button>
              <button
                type="button"
                disabled={loading}
                onClick={() => handleExecuteDecision("FORWARD")}
                className="rounded-xl bg-teal-600 px-5 py-2 text-xs font-bold text-white hover:bg-teal-500 disabled:opacity-50 transition shadow-sm"
              >
                {loading ? "Processing..." : "Confirm Forward →"}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* APPROVE & PROVISION CONFIRMATION MODAL */}
      {activeModal === "APPROVE" && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/75 backdrop-blur-md p-4 animate-fade-in-up">
          <div className="w-full max-w-md rounded-2xl border border-emerald-500/30 bg-slate-900 p-6 space-y-4 shadow-2xl text-slate-100">
            <div className="flex items-center gap-2 text-emerald-400 font-bold text-base">
              <CheckCircle2 className="w-5 h-5 text-emerald-400" />
              <span>Final Central Approval & Account Provisioning</span>
            </div>
            <p className="text-xs text-slate-400 leading-relaxed">
              This action will approve <strong className="text-slate-100">{application.applicant_name}</strong> and immediately provision their operational healthcare account.
              An activation invitation with an outbox event will be created in the database transaction.
            </p>
            <div>
              <label className="block text-xs font-semibold text-slate-300 mb-1">Approval Endorsement Remarks (Optional)</label>
              <textarea
                rows={3}
                value={decisionRemarks}
                onChange={(e) => setDecisionRemarks(e.target.value)}
                placeholder="e.g. Cleared under National Referral Registry guidelines."
                className="w-full rounded-xl border border-slate-700 bg-slate-950 p-3 text-xs text-slate-100 placeholder-slate-500 outline-none focus:border-emerald-500 focus:ring-2 focus:ring-emerald-500/20 transition"
              />
            </div>
            <div className="flex justify-end gap-3 pt-2">
              <button
                type="button"
                onClick={() => setActiveModal(null)}
                className="rounded-xl border border-slate-700 bg-slate-800 px-4 py-2 text-xs font-bold text-slate-300 hover:bg-slate-700 transition"
              >
                Cancel
              </button>
              <button
                type="button"
                disabled={loading}
                onClick={() => handleExecuteDecision("APPROVE")}
                className="rounded-xl bg-gradient-to-r from-emerald-600 to-teal-600 px-5 py-2 text-xs font-bold text-white hover:from-emerald-500 hover:to-teal-500 disabled:opacity-50 transition shadow-sm"
              >
                {loading ? "Provisioning..." : "Final Approve & Provision ✓"}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* REJECT CONFIRMATION MODAL */}
      {activeModal === "REJECT" && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/75 backdrop-blur-md p-4 animate-fade-in-up">
          <div className="w-full max-w-md rounded-2xl border border-rose-500/30 bg-slate-900 p-6 space-y-4 shadow-2xl text-slate-100">
            <div className="flex items-center gap-2 text-rose-400 font-bold text-base">
              <XCircle className="w-5 h-5 text-rose-400" />
              <span>Reject Application</span>
            </div>
            <p className="text-xs text-slate-400">
              Rejecting will permanently terminate the application review lifecycle. A formal reason is mandatory.
            </p>
            <div>
              <label className="block text-xs font-semibold text-slate-300 mb-1">Mandatory Rejection Reason *</label>
              <textarea
                rows={3}
                value={decisionRemarks}
                onChange={(e) => setDecisionRemarks(e.target.value)}
                placeholder="Provide a detailed, verifiable reason for rejection..."
                className="w-full rounded-xl border border-slate-700 bg-slate-950 p-3 text-xs text-slate-100 placeholder-slate-500 outline-none focus:border-rose-500 focus:ring-2 focus:ring-rose-500/20 transition"
                required
              />
            </div>
            <div className="flex justify-end gap-3 pt-2">
              <button
                type="button"
                onClick={() => setActiveModal(null)}
                className="rounded-xl border border-slate-700 bg-slate-800 px-4 py-2 text-xs font-bold text-slate-300 hover:bg-slate-700 transition"
              >
                Cancel
              </button>
              <button
                type="button"
                disabled={loading || !decisionRemarks.trim()}
                onClick={() => handleExecuteDecision("REJECT")}
                className="rounded-xl bg-rose-600 px-5 py-2 text-xs font-bold text-white hover:bg-rose-500 disabled:opacity-50 transition shadow-sm"
              >
                {loading ? "Rejecting..." : "Confirm Rejection ✕"}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* REQUEST CORRECTION MODAL */}
      {activeModal === "CORRECTION" && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/75 backdrop-blur-md p-4 animate-fade-in-up">
          <form
            onSubmit={handleExecuteCorrection}
            className="w-full max-w-md rounded-2xl border border-amber-500/30 bg-slate-900 p-6 space-y-4 shadow-2xl text-slate-100"
          >
            <div className="flex items-center gap-2 text-amber-400 font-bold text-base">
              <AlertTriangle className="w-5 h-5 text-amber-400" />
              <span>Request Applicant Corrections</span>
            </div>
            <p className="text-xs text-slate-400">
              The application will be set to <strong className="text-amber-400">CORRECTION_REQUIRED</strong>. The applicant can log in to update documents and submit a resubmission notes summary.
            </p>
            <div>
              <label className="block text-xs font-semibold text-slate-300 mb-1">Correction Instructions for Applicant *</label>
              <textarea
                rows={4}
                value={correctionNotes}
                onChange={(e) => setCorrectionNotes(e.target.value)}
                placeholder="e.g. Please re-upload Fire Safety NOC with clear endorsement seal and update emergency bed count."
                className="w-full rounded-xl border border-slate-700 bg-slate-950 p-3 text-xs text-slate-100 placeholder-slate-500 outline-none focus:border-amber-500 focus:ring-2 focus:ring-amber-500/20 transition"
                required
              />
            </div>
            <div className="flex justify-end gap-3 pt-2">
              <button
                type="button"
                onClick={() => setActiveModal(null)}
                className="rounded-xl border border-slate-700 bg-slate-800 px-4 py-2 text-xs font-bold text-slate-300 hover:bg-slate-700 transition"
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={loading || correctionNotes.trim().length < 5}
                className="rounded-xl bg-amber-600 px-5 py-2 text-xs font-bold text-white hover:bg-amber-500 disabled:opacity-50 transition shadow-sm"
              >
                {loading ? "Sending..." : "Submit Correction Request →"}
              </button>
            </div>
          </form>
        </div>
      )}

      {/* REJECT SPECIFIC DOCUMENT MODAL */}
      {activeModal === "DOC_REJECT" && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/75 backdrop-blur-md p-4 animate-fade-in-up">
          <form
            onSubmit={handleConfirmDocReject}
            className="w-full max-w-md rounded-2xl border border-rose-500/30 bg-slate-900 p-6 space-y-4 shadow-2xl text-slate-100"
          >
            <div className="flex items-center gap-2 text-rose-400 font-bold text-base">
              <XCircle className="w-5 h-5 text-rose-400" />
              <span>Reject Document</span>
            </div>
            <p className="text-xs text-slate-400">
              Specify the reason why this document does not meet compliance standards.
            </p>
            <div>
              <label className="block text-xs font-semibold text-slate-300 mb-1">Reviewer Rejection Reason *</label>
              <textarea
                rows={3}
                value={docRejectRemarks}
                onChange={(e) => setDocRejectRemarks(e.target.value)}
                placeholder="e.g. Certificate is illegible or expired on 2025-12-31."
                className="w-full rounded-xl border border-slate-700 bg-slate-950 p-3 text-xs text-slate-100 placeholder-slate-500 outline-none focus:border-rose-500 focus:ring-2 focus:ring-rose-500/20 transition"
                required
              />
            </div>
            <div className="flex justify-end gap-3 pt-2">
              <button
                type="button"
                onClick={() => setActiveModal(null)}
                className="rounded-xl border border-slate-700 bg-slate-800 px-4 py-2 text-xs font-bold text-slate-300 hover:bg-slate-700 transition"
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={loading || !docRejectRemarks.trim()}
                className="rounded-xl bg-rose-600 px-5 py-2 text-xs font-bold text-white hover:bg-rose-500 disabled:opacity-50 transition shadow-sm"
              >
                {loading ? "Submitting..." : "Reject Document"}
              </button>
            </div>
          </form>
        </div>
      )}

      {/* DOCUMENT PREVIEW MODAL */}
      {activeModal === "DOC_PREVIEW" && previewBlobUrl && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-md p-4 animate-fade-in-up">
          <div className="w-full max-w-4xl h-[85vh] rounded-2xl border border-slate-800 bg-slate-900 p-5 flex flex-col shadow-2xl text-slate-100">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <div className="flex items-center gap-2 truncate">
                <FileText className="w-5 h-5 text-teal-400" />
                <span className="text-sm font-bold text-slate-100 truncate">{previewFilename}</span>
                <span className="text-[11px] text-slate-400">({previewContentType})</span>
              </div>
              <div className="flex items-center gap-2">
                <a
                  href={previewBlobUrl}
                  download={previewFilename}
                  className="inline-flex items-center gap-1 rounded-lg border border-slate-700 bg-slate-800 px-3 py-1.5 text-xs font-bold text-slate-200 hover:bg-slate-700 transition shadow-2xs"
                >
                  <Download className="w-3.5 h-3.5 text-teal-400" />
                  <span>Download File</span>
                </a>
                <button
                  onClick={() => {
                    setActiveModal(null);
                    setPreviewBlobUrl(null);
                  }}
                  className="rounded-lg p-1.5 text-slate-400 hover:bg-slate-800 hover:text-white transition"
                  aria-label="Close document preview"
                >
                  <X className="w-5 h-5" />
                </button>
              </div>
            </div>

            <div className="flex-1 mt-4 overflow-hidden rounded-xl border border-slate-800 bg-slate-950 flex items-center justify-center">
              {previewContentType.includes("pdf") ? (
                <iframe src={previewBlobUrl} className="w-full h-full rounded-xl" title="Document Preview" />
              ) : previewContentType.includes("image") ? (
                <img
                  src={previewBlobUrl}
                  alt="Document Preview"
                  className="max-h-full max-w-full object-contain p-2"
                />
              ) : (
                <div className="text-center p-8 space-y-3">
                  <FileText className="w-12 h-12 text-slate-500 mx-auto" />
                  <p className="text-xs text-slate-300">Direct browser preview not supported for this format.</p>
                  <a
                    href={previewBlobUrl}
                    download={previewFilename}
                    className="inline-flex items-center gap-2 rounded-xl bg-teal-600 px-4 py-2 text-xs font-bold text-white hover:bg-teal-500 transition shadow-sm"
                  >
                    <Download className="w-4 h-4" />
                    <span>Download {previewFilename}</span>
                  </a>
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
