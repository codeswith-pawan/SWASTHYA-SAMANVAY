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

  const handleDelete = async (docId: string, slotType: string) => {
    if (!confirm("Are you sure you want to remove this document?")) return;

    setDeletingId(docId);
    setErrorMap((prev) => ({ ...prev, [slotType]: "" }));

    try {
      await apiDeleteDocument(docId, applicantToken);
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
            className={`rounded-2xl border p-4 sm:p-5 transition ${
              uploadedDoc
                ? uploadedDoc.verification_status === "REJECTED"
                  ? "border-rose-200 bg-rose-50/50"
                  : uploadedDoc.verification_status === "VERIFIED"
                  ? "border-emerald-200 bg-emerald-50/40"
                  : "border-slate-200 bg-slate-50/70"
                : "border-slate-200/90 bg-white"
            }`}
          >
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
              <div>
                <div className="flex items-center gap-2">
                  <span className="text-sm font-bold text-slate-900">{slot.label}</span>
                  {slot.required ? (
                    <span className="rounded bg-rose-50 px-2 py-0.5 text-[10px] font-bold text-rose-700 border border-rose-200">
                      Required
                    </span>
                  ) : (
                    <span className="rounded bg-slate-100 px-2 py-0.5 text-[10px] font-semibold text-slate-600 border border-slate-200">
                      Optional
                    </span>
                  )}
                </div>
                <p className="mt-1 text-xs text-slate-500 leading-relaxed">{slot.description}</p>
              </div>

              {/* Status Badge */}
              {uploadedDoc && (
                <div className="flex items-center gap-2 shrink-0">
                  {uploadedDoc.verification_status === "VERIFIED" && (
                    <span className="inline-flex items-center gap-1 rounded-full border border-emerald-300 bg-emerald-50 px-2.5 py-0.5 text-xs font-bold text-emerald-800">
                      <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600" />
                      <span>Verified</span>
                    </span>
                  )}
                  {uploadedDoc.verification_status === "REJECTED" && (
                    <span className="inline-flex items-center gap-1 rounded-full border border-rose-300 bg-rose-50 px-2.5 py-0.5 text-xs font-bold text-rose-800">
                      <AlertCircle className="w-3.5 h-3.5 text-rose-600" />
                      <span>Rejected</span>
                    </span>
                  )}
                  {uploadedDoc.verification_status === "PENDING" && (
                    <span className="inline-flex items-center gap-1 rounded-full border border-teal-300 bg-teal-50 px-2.5 py-0.5 text-xs font-bold text-teal-800">
                      <RefreshCw className="w-3.5 h-3.5 text-teal-600 animate-spin" />
                      <span>Pending Review</span>
                    </span>
                  )}
                </div>
              )}
            </div>

            {/* If uploaded */}
            {uploadedDoc ? (
              <div className="mt-4 rounded-xl border border-slate-200 bg-white p-3.5 shadow-2xs">
                <div className="flex flex-wrap items-center justify-between gap-3">
                  <div className="flex items-center gap-2.5 min-w-0">
                    <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-teal-50 border border-teal-200 text-teal-700">
                      <FileText className="w-5 h-5" />
                    </div>
                    <div className="min-w-0">
                      <p className="text-xs font-bold text-slate-900 truncate">
                        {uploadedDoc.original_filename}
                      </p>
                      <p className="text-[11px] text-slate-500">
                        {formatBytes(uploadedDoc.file_size_bytes)} • Uploaded{" "}
                        {new Date(uploadedDoc.uploaded_at).toLocaleDateString()}
                      </p>
                    </div>
                  </div>

                  {canEdit && (
                    <div className="flex items-center gap-2">
                      <label className="cursor-pointer rounded-lg border border-slate-300 bg-slate-50 px-3 py-1.5 text-[11px] font-semibold text-slate-700 hover:bg-slate-100 transition shadow-2xs">
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
                        className="rounded-lg border border-rose-300 bg-rose-50 px-3 py-1.5 text-[11px] font-semibold text-rose-700 hover:bg-rose-100 transition disabled:opacity-50 inline-flex items-center gap-1 shadow-2xs"
                      >
                        <Trash2 className="w-3.5 h-3.5" />
                        <span>{deletingId === uploadedDoc.document_id ? "Removing..." : "Remove"}</span>
                      </button>
                    </div>
                  )}
                </div>

                {/* Reviewer remarks if rejected */}
                {uploadedDoc.reviewer_remarks && (
                  <div className="mt-3 rounded-lg border border-rose-200 bg-rose-50 p-2.5 text-xs text-rose-800">
                    <strong className="font-semibold">Reviewer Reason:</strong> {uploadedDoc.reviewer_remarks}
                  </div>
                )}
              </div>
            ) : (
              /* Upload Dropzone Area */
              canEdit && (
                <div className="mt-3">
                  <label
                    className={`flex flex-col items-center justify-center rounded-xl border-2 border-dashed border-slate-300 bg-slate-50/70 hover:bg-teal-50/40 hover:border-teal-500 px-4 py-5 text-center cursor-pointer transition ${
                      isUploading ? "opacity-50 pointer-events-none" : ""
                    }`}
                  >
                    <UploadCloud className="w-6 h-6 text-teal-600 mb-1" />
                    <span className="text-xs font-bold text-slate-800">
                      {isUploading ? "Uploading & scanning document..." : "Click to select or drag and drop file"}
                    </span>
                    <span className="mt-1 text-[11px] text-slate-500">
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
              <div className="mt-2.5 rounded-lg border border-rose-200 bg-rose-50 p-2.5 text-xs text-rose-800">
                {err}
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
};
