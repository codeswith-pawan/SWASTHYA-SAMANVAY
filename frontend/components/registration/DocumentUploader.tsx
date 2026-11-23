"use client";

import React, { useState } from "react";
import { DocumentMetadata, DocumentType } from "@/lib/types";
import { apiUploadDocument, apiDeleteDocument } from "@/lib/api";
import { FileText, UploadCloud, Trash2, CheckCircle2, AlertCircle, RefreshCw } from "lucide-react";

interface DocumentSlot {
  type: DocumentType;
  label: string;
  description: string;
  required: boolean;
}

interface DocumentUploaderProps {
  slots: DocumentSlot[];
  existingDocuments: DocumentMetadata[];
  applicantToken?: string | null;
  canEdit?: boolean;
  onDocumentsChanged: () => void;
}

const MAX_FILE_SIZE = 25 * 1024 * 1024; // 25 MB
const ALLOWED_MIME_TYPES = ["application/pdf", "image/jpeg", "image/png"];

export const DocumentUploader: React.FC<DocumentUploaderProps> = ({
  slots,
  existingDocuments,
  applicantToken,
  canEdit = true,
  onDocumentsChanged,
}) => {
  const [uploadingType, setUploadingType] = useState<string | null>(null);
  const [deletingId, setDeletingId] = useState<string | null>(null);
  const [errorMap, setErrorMap] = useState<Record<string, string>>({});

  const formatBytes = (bytes: number) => {
    if (bytes === 0) return "0 Bytes";
    const k = 1024;
    const sizes = ["Bytes", "KB", "MB"];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + " " + sizes[i];
  };

  const handleFileSelect = async (slotType: DocumentType, file: File | null) => {
    if (!file) return;

    setErrorMap((prev) => ({ ...prev, [slotType]: "" }));

    if (!ALLOWED_MIME_TYPES.includes(file.type)) {
      setErrorMap((prev) => ({
        ...prev,
        [slotType]: "Invalid file format. Allowed formats: PDF (.pdf), JPEG (.jpg, .jpeg), PNG (.png).",
      }));
      return;
    }

    if (file.size > MAX_FILE_SIZE) {
      setErrorMap((prev) => ({
        ...prev,
        [slotType]: `File exceeds maximum allowed size of 25 MB (${formatBytes(file.size)}).`,
      }));
      return;
    }

    setUploadingType(slotType);

    try {
      await apiUploadDocument(slotType, file, applicantToken);
      onDocumentsChanged();
    } catch (err: any) {
      setErrorMap((prev) => ({
        ...prev,
        [slotType]: err.message || "Upload failed. Please verify the document meets guidelines.",
      }));
    } finally {
      setUploadingType(null);
    }
  };

  const handleDelete = async (documentId: string, slotType: string) => {
    if (!confirm("Are you sure you want to remove this uploaded document?")) return;
    setDeletingId(documentId);
    setErrorMap((prev) => ({ ...prev, [slotType]: "" }));

    try {
      await apiDeleteDocument(documentId, applicantToken);
      onDocumentsChanged();
    } catch (err: any) {
      setErrorMap((prev) => ({
        ...prev,
        [slotType]: err.message || "Failed to remove document.",
      }));
    } finally {
      setDeletingId(null);
    }
  };

  return (
    <div className="space-y-4">
      {slots.map((slot) => {
        const uploadedDoc = existingDocuments.find((d) => d.document_type === slot.type);
        const isUploading = uploadingType === slot.type;
        const err = errorMap[slot.type];

        return (
          <div
            key={slot.type}
            className="rounded-2xl border border-slate-800 bg-slate-900/90 p-4 sm:p-5 shadow-xs transition hover:border-slate-700"
          >
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div className="space-y-1">
                <div className="flex items-center gap-2">
                  <h4 className="text-sm font-bold text-slate-100">{slot.label}</h4>
                  {slot.required ? (
                    <span className="rounded-full bg-rose-500/10 border border-rose-500/30 px-2 py-0.5 text-[10px] font-bold text-rose-400">
                      Required
                    </span>
                  ) : (
                    <span className="rounded-full bg-slate-800 border border-slate-700 px-2 py-0.5 text-[10px] font-bold text-slate-400">
                      Optional
                    </span>
                  )}
                </div>
                <p className="text-xs text-slate-400 max-w-xl">{slot.description}</p>
              </div>

              {uploadedDoc && (
                <div>
                  {uploadedDoc.verification_status === "VERIFIED" && (
                    <span className="inline-flex items-center gap-1 rounded-full border border-emerald-500/30 bg-emerald-950/40 px-2.5 py-0.5 text-xs font-bold text-emerald-300">
                      <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
                      <span>Verified</span>
                    </span>
                  )}
                  {uploadedDoc.verification_status === "REJECTED" && (
                    <span className="inline-flex items-center gap-1 rounded-full border border-rose-500/30 bg-rose-950/40 px-2.5 py-0.5 text-xs font-bold text-rose-300">
                      <AlertCircle className="w-3.5 h-3.5 text-rose-400" />
                      <span>Rejected</span>
                    </span>
                  )}
                  {uploadedDoc.verification_status === "PENDING" && (
                    <span className="inline-flex items-center gap-1 rounded-full border border-teal-500/30 bg-teal-950/40 px-2.5 py-0.5 text-xs font-bold text-teal-300">
                      <RefreshCw className="w-3.5 h-3.5 text-teal-400 animate-spin" />
                      <span>Pending Review</span>
                    </span>
                  )}
                </div>
              )}
            </div>

            {/* If uploaded */}
            {uploadedDoc ? (
              <div className="mt-4 rounded-xl border border-slate-800 bg-slate-950/60 p-3.5 shadow-2xs">
                <div className="flex flex-wrap items-center justify-between gap-3">
                  <div className="flex items-center gap-2.5 min-w-0">
                    <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-teal-500/10 border border-teal-500/20 text-teal-400">
                      <FileText className="w-5 h-5" />
                    </div>
                    <div className="min-w-0">
                      <p className="text-xs font-bold text-slate-100 truncate">
                        {uploadedDoc.original_filename}
                      </p>
                      <p className="text-[11px] text-slate-400">
                        {formatBytes(uploadedDoc.file_size_bytes)} • Uploaded{" "}
                        {new Date(uploadedDoc.uploaded_at).toLocaleDateString()}
                      </p>
                    </div>
                  </div>

                  {canEdit && (
                    <div className="flex items-center gap-2">
                      <label className="cursor-pointer rounded-lg border border-slate-700 bg-slate-800/80 px-3 py-1.5 text-[11px] font-semibold text-slate-300 hover:bg-slate-800 hover:text-white transition shadow-2xs">
                        Replace File
                        <input
                          type="file"
                          accept=".pdf,.jpg,.jpeg,.png"
                          className="hidden"
                          onChange={(e) => handleFileSelect(slot.type, e.target.files?.[0] || null)}
                          disabled={isUploading}
                        />
                      </label>
                      <button
                        type="button"
                        onClick={() => handleDelete(uploadedDoc.document_id, slot.type)}
                        disabled={deletingId === uploadedDoc.document_id}
                        className="rounded-lg border border-rose-500/30 bg-rose-950/40 px-3 py-1.5 text-[11px] font-semibold text-rose-300 hover:bg-rose-900/40 transition disabled:opacity-50 inline-flex items-center gap-1 shadow-2xs"
                      >
                        <Trash2 className="w-3.5 h-3.5" />
                        <span>{deletingId === uploadedDoc.document_id ? "Removing..." : "Remove"}</span>
                      </button>
                    </div>
                  )}
                </div>

                {/* Reviewer remarks if rejected */}
                {uploadedDoc.reviewer_remarks && (
                  <div className="mt-3 rounded-lg border border-rose-500/30 bg-rose-950/40 p-2.5 text-xs text-rose-300">
                    <strong className="font-semibold">Reviewer Reason:</strong> {uploadedDoc.reviewer_remarks}
                  </div>
                )}
              </div>
            ) : (
              /* Upload Dropzone Area */
              canEdit && (
                <div className="mt-3">
                  <label
                    className={`flex flex-col items-center justify-center rounded-xl border-2 border-dashed border-slate-700 bg-slate-950/40 hover:bg-teal-950/20 hover:border-teal-500/60 px-4 py-5 text-center cursor-pointer transition ${
                      isUploading ? "opacity-50 pointer-events-none" : ""
                    }`}
                  >
                    <UploadCloud className="w-6 h-6 text-teal-400 mb-1" />
                    <span className="text-xs font-bold text-slate-200">
                      {isUploading ? "Uploading & scanning document..." : "Click to select or drag and drop file"}
                    </span>
                    <span className="mt-1 text-[11px] text-slate-400">
                      Accepted: PDF, JPEG, or PNG (up to 25 MB)
                    </span>
                    <input
                      type="file"
                      accept=".pdf,.jpg,.jpeg,.png"
                      className="hidden"
                      onChange={(e) => handleFileSelect(slot.type, e.target.files?.[0] || null)}
                      disabled={isUploading}
                    />
                  </label>
                </div>
              )
            )}

            {/* Error banner */}
            {err && (
              <div className="mt-2.5 rounded-lg border border-rose-500/30 bg-rose-950/40 p-2.5 text-xs text-rose-300">
                {err}
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
};
