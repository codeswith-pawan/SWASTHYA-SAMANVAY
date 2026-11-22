"use client";

import React, { useState, useEffect } from "react";
import Link from "next/link";
import {
  ShieldCheck,
  Lock,
  FileText,
  AlertTriangle,
  CheckCircle2,
  ArrowRight,
  LogOut,
  Building,
  User,
  Phone,
  Mail,
  MapPin,
  RefreshCw,
  Clock,
} from "lucide-react";
import { RegistrationNavbar } from "@/components/registration/RegistrationNavbar";
import { ApplicationTimeline } from "@/components/registration/ApplicationTimeline";
import { DocumentUploader } from "@/components/registration/DocumentUploader";
import { OTPModal } from "@/components/registration/OTPModal";
import { NotificationPanel } from "@/components/shared/NotificationPanel";
import {
  apiGetMyApplication,
  apiSubmitApplication,
  apiResubmitApplication,
  apiGetApplicantNotifications,
  apiMarkApplicantNotificationRead,
  apiMarkAllApplicantNotificationsRead,
  getApplicantToken,
  setApplicantToken,
  clearApplicantToken,
} from "@/lib/api";
import { ApplicantApplication, DocumentType, OTPVerifyResponse, NotificationItem } from "@/lib/types";

const ALL_DOC_SLOTS = [
  {
    type: "CLINICAL_LICENSE" as DocumentType,
    label: "Clinical Establishment Registration",
    description: "Valid certificate under Clinical Establishments Act.",
    required: true,
  },
  {
    type: "FIRE_SAFETY_NOC" as DocumentType,
    label: "Fire Safety NOC Clearance",
    description: "Fire department safety compliance and clearance certificate.",
    required: true,
  },
  {
    type: "GOVERNMENT_ORDER" as DocumentType,
    label: "Government Order / Authorization Notification",
    description: "Official gazetted order appointing the CMO / authorizing state or district onboarding.",
    required: true,
  },
  {
    type: "POLLUTION_CONTROL_NOC" as DocumentType,
    label: "Bio-Medical Waste NOC",
    description: "State Pollution Control Board authorization.",
    required: false,
  },
  {
    type: "MEDICAL_COUNCIL_AFFILIATION" as DocumentType,
    label: "Accreditation / Medical Council",
    description: "NMC / NABH / NABL certificate.",
    required: false,
  },
];

export default function ApplicationStatusPage() {
  const [mounted, setMounted] = useState(false);
  const [applicantTokenState, setApplicantTokenState] = useState<string | null>(null);
  const [application, setApplication] = useState<ApplicantApplication | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  // Applicant OTP Login Form States
  const [loginAppNumber, setLoginAppNumber] = useState("");
  const [loginContact, setLoginContact] = useState("");
  const [isOtpModalOpen, setIsOtpModalOpen] = useState(false);

  // Correction Resubmission States
  const [resubmissionNotes, setResubmissionNotes] = useState("");
  const [resubmitting, setResubmitting] = useState(false);
  const [submittingDraft, setSubmittingDraft] = useState(false);
  const [actionSuccess, setActionSuccess] = useState("");

  // Applicant Notifications State
  const [notifications, setNotifications] = useState<NotificationItem[]>([]);
  const [unreadCount, setUnreadCount] = useState(0);
  const [notifLoading, setNotifLoading] = useState(false);

  const loadApplicantNotifications = async () => {
    setNotifLoading(true);
    try {
      const data = await apiGetApplicantNotifications();
      setNotifications(data.notifications || []);
      setUnreadCount(data.unread_count || 0);
    } catch {
      // background poll failure
    } finally {
      setNotifLoading(false);
    }
  };

  const fetchApplication = async (token = applicantTokenState) => {
    if (!token) return;
    setLoading(true);
    setError("");

    try {
      const data = await apiGetMyApplication(token);
      setApplication(data);
      loadApplicantNotifications();
    } catch (err: any) {
      setError(err.message || "Failed to load application details. Please re-authenticate.");
      clearApplicantToken();
      setApplicantTokenState(null);
      setApplication(null);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    setMounted(true);
    const storedToken = getApplicantToken();
    if (storedToken) {
      setApplicantTokenState(storedToken);
      fetchApplication(storedToken);
    }
  }, []);

  const handleStartOtpLogin = (e: React.FormEvent) => {
    e.preventDefault();
    setError("");

    if (!loginAppNumber.trim() || !loginContact.trim()) {
      setError("Please provide both your Application Number and registered Email/Phone.");
      return;
    }

    setIsOtpModalOpen(true);
  };

  const handleOtpVerified = (response: OTPVerifyResponse) => {
    if (response.applicant_token) {
      setApplicantToken(response.applicant_token);
      setApplicantTokenState(response.applicant_token);
      fetchApplication(response.applicant_token);
      setIsOtpModalOpen(false);
    } else {
      setError("Verification succeeded but no applicant session token was issued.");
    }
  };

  const handleSignOut = () => {
    clearApplicantToken();
    setApplicantTokenState(null);
    setApplication(null);
    setError("");
    setActionSuccess("");
  };

  const handleSubmitDraft = async () => {
    if (!applicantTokenState) return;
    setSubmittingDraft(true);
    setError("");
    setActionSuccess("");

    try {
      const res = await apiSubmitApplication("Submitted via applicant portal", applicantTokenState);
      setActionSuccess(`Application ${res.application_number} submitted successfully for review.`);
      fetchApplication();
    } catch (err: any) {
      setError(err.message || "Draft submission failed.");
    } finally {
      setSubmittingDraft(false);
    }
  };

  const handleResubmitCorrection = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!applicantTokenState) return;
    if (resubmissionNotes.trim().length < 5) {
      setError("Please explain the corrections made (minimum 5 characters).");
      return;
    }

    setResubmitting(true);
    setError("");
    setActionSuccess("");

    try {
      const res = await apiResubmitApplication(resubmissionNotes.trim(), applicantTokenState);
      setActionSuccess(`Application v${res.resubmission_version} resubmitted successfully for review.`);
      setResubmissionNotes("");
      fetchApplication();
    } catch (err: any) {
      setError(err.message || "Resubmission failed.");
    } finally {
      setResubmitting(false);
    }
  };

  if (!mounted) {
    return (
      <div className="min-h-screen bg-slate-50 text-slate-800 flex items-center justify-center">
        <div className="text-xs text-slate-500 flex items-center gap-2">
          <RefreshCw className="w-4 h-4 animate-spin text-teal-600" />
          Loading applicant session...
        </div>
      </div>
    );
  }

  // Filter slots relevant to applicant type
  const relevantSlots = ALL_DOC_SLOTS.filter((s) => {
    if (application?.applicant_type === "HOSPITAL") {
      return s.type !== "GOVERNMENT_ORDER";
    }
    if (application?.applicant_type === "DISTRICT" || application?.applicant_type === "STATE") {
      return s.type === "GOVERNMENT_ORDER" || s.type === "IDENTITY_PROOF";
    }
    return true;
  });

  const isCorrectionRequired = application?.status === "CORRECTION_REQUIRED";
  const isDraft = application?.status === "DRAFT";
  const canEditDocuments = isDraft || isCorrectionRequired;

  return (
    <div className="min-h-screen bg-[#F4F8FC] text-[#14243B] flex flex-col font-sans">
      <RegistrationNavbar />

      <main className="flex-1 mx-auto w-full max-w-5xl px-4 sm:px-6 py-8 sm:py-10 space-y-8">
        {/* Top Header */}
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div>
            <nav className="flex items-center gap-2 text-xs font-medium text-slate-500 mb-1">
              <Link href="/" className="hover:text-teal-700 transition">Portal Home</Link>
              <span>/</span>
              <Link href="/register" className="hover:text-teal-700 transition">Registration Hub</Link>
              <span>/</span>
              <span className="text-slate-800 font-semibold">Applicant Portal</span>
            </nav>
            <h1 className="text-2xl sm:text-3xl font-extrabold text-slate-900 tracking-tight">
              Applicant Dashboard & Document Management
            </h1>
            <p className="text-xs sm:text-sm text-slate-600 mt-0.5">
              Securely view official verification remarks, replace requested documents, and resubmit applications.
            </p>
          </div>

          {application && (
            <div className="flex items-center gap-3">
              <NotificationPanel
                notifications={notifications}
                unreadCount={unreadCount}
                loading={notifLoading}
                onMarkRead={(nid) => {
                  apiMarkApplicantNotificationRead(nid).then(loadApplicantNotifications);
                }}
                onMarkAllRead={() => {
                  apiMarkAllApplicantNotificationsRead().then(loadApplicantNotifications);
                }}
                onRefresh={loadApplicantNotifications}
              />
              <button
                onClick={handleSignOut}
                className="inline-flex items-center gap-1.5 rounded-xl border border-slate-200 bg-white px-4 py-2 text-xs font-semibold text-slate-700 hover:bg-slate-50 hover:border-slate-300 transition shadow-sm"
              >
                <LogOut className="w-3.5 h-3.5" />
                Sign Out
              </button>
            </div>
          )}
        </div>

        {/* Global Notices */}
        {error && (
          <div className="rounded-2xl border border-rose-200 bg-rose-50/80 p-4 text-xs sm:text-sm text-rose-800 flex items-start gap-3 shadow-sm animate-fade-in-up">
            <AlertTriangle className="w-5 h-5 text-rose-600 shrink-0 mt-0.5" />
            <div className="flex-1 font-medium leading-relaxed">{error}</div>
          </div>
        )}

        {actionSuccess && (
          <div className="rounded-2xl border border-emerald-200 bg-emerald-50/80 p-4 text-xs sm:text-sm text-emerald-800 flex items-start gap-3 shadow-sm animate-fade-in-up">
            <CheckCircle2 className="w-5 h-5 text-emerald-600 shrink-0 mt-0.5" />
            <div className="flex-1 font-medium leading-relaxed">{actionSuccess}</div>
          </div>
        )}

        {/* VIEW 1: UN-AUTHENTICATED APPLICANT LOGIN */}
        {!application && !loading && (
          <div className="max-w-md mx-auto rounded-3xl border border-slate-200/80 bg-white/95 backdrop-blur-sm p-6 sm:p-8 shadow-[0_8px_30px_rgb(15,23,42,0.08)] space-y-6">
            <div className="text-center space-y-2">
              <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-2xl bg-teal-50 border border-teal-200 text-teal-700 shadow-sm">
                <Lock className="w-6 h-6" />
              </div>
              <h2 className="text-xl font-bold text-slate-900">Applicant Two-Factor Sign In</h2>
              <p className="text-xs text-slate-500">
                Access your registered application record by entering your application number and registered email/phone.
              </p>
            </div>

            <form onSubmit={handleStartOtpLogin} className="space-y-4">
              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">
                  Application Number <span className="text-rose-500">*</span>
                </label>
                <input
                  type="text"
                  value={loginAppNumber}
                  onChange={(e) => setLoginAppNumber(e.target.value)}
                  placeholder="e.g. APP-HOSP-202611-ABC123"
                  className="w-full rounded-xl border border-slate-300 bg-slate-50/50 px-3.5 py-2.5 text-xs sm:text-sm text-slate-900 placeholder-slate-400 focus:bg-white focus:border-teal-600 focus:ring-4 focus:ring-teal-500/10 font-mono outline-none transition-all"
                  required
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">
                  Registered Official Email / Phone <span className="text-rose-500">*</span>
                </label>
                <input
                  type="text"
                  value={loginContact}
                  onChange={(e) => setLoginContact(e.target.value)}
                  placeholder="e.g. nodal.officer@punjab.gov.in"
                  className="w-full rounded-xl border border-slate-300 bg-slate-50/50 px-3.5 py-2.5 text-xs sm:text-sm text-slate-900 placeholder-slate-400 focus:bg-white focus:border-teal-600 focus:ring-4 focus:ring-teal-500/10 outline-none transition-all"
                  required
                />
              </div>

              <button
                type="submit"
                className="w-full inline-flex items-center justify-center gap-2 rounded-xl bg-gradient-to-r from-teal-600 to-emerald-600 py-3 text-xs sm:text-sm font-bold text-white hover:from-teal-700 hover:to-emerald-700 transition shadow-md shadow-teal-600/20"
              >
                Send 2FA Security Code <ArrowRight className="w-4 h-4" />
              </button>
            </form>

            <div className="border-t border-slate-100 pt-4 text-center">
              <Link href="/register" className="text-xs font-semibold text-teal-700 hover:text-teal-800 transition">
                Need to create a new application? Register here →
              </Link>
            </div>
          </div>
        )}

        {/* VIEW 2: AUTHENTICATED APPLICANT DASHBOARD */}
        {application && (
          <div className="space-y-8">
            {/* CORRECTION REQUIRED NOTICE BANNER */}
            {isCorrectionRequired && (
              <div className="rounded-2xl border border-amber-300 bg-amber-50/80 p-5 sm:p-6 space-y-3 shadow-sm animate-fade-in-up">
                <div className="flex items-center gap-2 text-amber-900 font-bold text-sm">
                  <AlertTriangle className="w-5 h-5 text-amber-700 shrink-0" />
                  <span>Action Required: Reviewer Requested Corrections (v{application.resubmission_version})</span>
                </div>
                <p className="text-xs text-amber-800 leading-relaxed">
                  The reviewing authority examined your application and requested adjustments before clearance.
                  Please review the specific correction instructions below, update the affected documents, and submit your corrections.
                </p>
                {application.correction_notes && (
                  <div className="rounded-xl border border-amber-200 bg-white/90 p-4 text-xs font-mono text-amber-950 shadow-inner">
                    <strong className="font-sans font-bold block mb-1 text-amber-900">
                      Official Reviewer Note:
                    </strong>
                    {application.correction_notes}
                  </div>
                )}
              </div>
            )}

            {/* Application Overview Card */}
            <div className="rounded-2xl border border-slate-200/80 border-t-4 border-t-teal-600 bg-white/95 backdrop-blur-sm p-6 sm:p-7 space-y-5 shadow-[0_8px_30px_rgb(15,23,42,0.06)]">
              <div className="flex flex-wrap items-center justify-between gap-4 border-b border-slate-100 pb-4">
                <div>
                  <span className="rounded-full bg-teal-50 px-2.5 py-0.5 text-[10px] font-bold text-teal-700 border border-teal-200 uppercase tracking-wider">
                    {application.applicant_type} Facility Record
                  </span>
                  <h2 className="mt-2 text-xl font-bold text-slate-900">{application.applicant_name}</h2>
                  <p className="text-xs text-slate-500">
                    Jurisdiction: {application.district ? `${application.district}, ` : ""}{application.state}
                  </p>
                </div>

                <div className="text-right">
                  <span className="text-[11px] text-slate-500 font-mono block">Application Number</span>
                  <span className="text-sm font-mono font-bold text-teal-700">
                    {application.application_number}
                  </span>
                </div>
              </div>

              {/* Facility & Contact Grid */}
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 text-xs">
                <div className="rounded-xl border border-slate-200 bg-slate-50/70 p-4 space-y-2">
                  <h4 className="font-bold text-slate-800 uppercase tracking-wider text-[11px] flex items-center gap-1.5">
                    <User className="w-3.5 h-3.5 text-teal-700" /> Designated Nodal Officer
                  </h4>
                  <p className="text-slate-600">Name: <strong className="text-slate-900">{application.nodal_officer_name || "N/A"}</strong></p>
                  <p className="text-slate-600">Designation: <strong className="text-slate-900">{application.official_designation || "N/A"}</strong></p>
                </div>

                <div className="rounded-xl border border-slate-200 bg-slate-50/70 p-4 space-y-2">
                  <h4 className="font-bold text-slate-800 uppercase tracking-wider text-[11px] flex items-center gap-1.5">
                    <Mail className="w-3.5 h-3.5 text-teal-700" /> Contact Information
                  </h4>
                  <p className="text-slate-600">Email: <strong className="text-slate-900">{application.applicant_email}</strong></p>
                  <p className="text-slate-600">Phone: <strong className="text-slate-900">{application.applicant_phone}</strong></p>
                </div>

                <div className="rounded-xl border border-slate-200 bg-slate-50/70 p-4 space-y-2">
                  <h4 className="font-bold text-slate-800 uppercase tracking-wider text-[11px] flex items-center gap-1.5">
                    <MapPin className="w-3.5 h-3.5 text-teal-700" /> Address & Location
                  </h4>
                  <p className="text-slate-600 truncate">Street: <strong className="text-slate-900">{application.address || "N/A"}</strong></p>
                  <p className="text-slate-600">PIN Code: <strong className="text-slate-900">{application.pincode || "N/A"}</strong></p>
                </div>
              </div>
            </div>

            {/* Stepper Timeline */}
            <ApplicationTimeline
              status={application.status}
              currentStage={application.current_stage}
              milestones={application.milestones}
              resubmissionVersion={application.resubmission_version}
            />

            {/* Document Management Section */}
            <div className="rounded-2xl border border-slate-200/80 bg-white/95 backdrop-blur-sm p-6 sm:p-7 space-y-5 shadow-[0_8px_30px_rgb(15,23,42,0.06)]">
              <div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-100 pb-4">
                <div>
                  <h3 className="text-base font-bold text-slate-900">Regulatory Documentation</h3>
                  <p className="text-xs text-slate-500 mt-0.5">
                    {canEditDocuments
                      ? "You may upload new or replacement certificates below."
                      : "Document repository is locked while under active government review."}
                  </p>
                </div>

                {isDraft && (
                  <button
                    type="button"
                    onClick={handleSubmitDraft}
                    disabled={submittingDraft}
                    className="inline-flex items-center gap-2 rounded-xl bg-gradient-to-r from-teal-600 to-emerald-600 px-5 py-2.5 text-xs font-bold text-white hover:from-teal-700 hover:to-emerald-700 disabled:opacity-50 transition shadow-md shadow-teal-600/20"
                  >
                    {submittingDraft ? "Submitting..." : "Submit Draft Application"}
                    <ArrowRight className="w-4 h-4" />
                  </button>
                )}
              </div>

              <DocumentUploader
                slots={relevantSlots}
                existingDocuments={application.documents}
                applicantToken={applicantTokenState}
                canEdit={canEditDocuments}
                onDocumentsChanged={() => fetchApplication()}
              />
            </div>

            {/* CORRECTION RESUBMISSION FORM */}
            {isCorrectionRequired && (
              <div className="rounded-2xl border border-amber-300 bg-amber-50/50 p-6 sm:p-8 space-y-5 shadow-sm">
                <div>
                  <span className="rounded-full bg-amber-100 px-2.5 py-0.5 text-[10px] font-bold text-amber-800 border border-amber-200 uppercase tracking-wider">
                    Resubmission Form
                  </span>
                  <h3 className="mt-2 text-base font-bold text-slate-900">
                    Submit Rectified Application for Review
                  </h3>
                  <p className="text-xs text-slate-600 mt-0.5">
                    Ensure all rejected documents have been replaced above. Provide a detailed note of corrections made for the reviewing officer.
                  </p>
                </div>

                <form onSubmit={handleResubmitCorrection} className="space-y-4">
                  <div>
                    <label className="block text-xs font-semibold text-slate-700 mb-1">
                      Applicant Correction Notes <span className="text-rose-500">*</span>
                    </label>
                    <textarea
                      rows={4}
                      value={resubmissionNotes}
                      onChange={(e) => setResubmissionNotes(e.target.value)}
                      placeholder="e.g. Uploaded renewed Fire Safety NOC dated 2026 and updated total bed breakdown as requested."
                      className="w-full rounded-xl border border-slate-300 bg-white p-3.5 text-xs sm:text-sm text-slate-900 placeholder-slate-400 outline-none focus:border-amber-500 focus:ring-4 focus:ring-amber-500/10 transition"
                      required
                    />
                  </div>

                  <div className="flex justify-end">
                    <button
                      type="submit"
                      disabled={resubmitting || resubmissionNotes.trim().length < 5}
                      className="inline-flex items-center gap-2 rounded-xl bg-amber-600 px-6 py-3 text-xs sm:text-sm font-bold text-white hover:bg-amber-700 disabled:opacity-50 transition shadow-md shadow-amber-600/20"
                    >
                      {resubmitting ? "Resubmitting..." : "Resubmit Application for Clearance"}
                      <ArrowRight className="w-4 h-4" />
                    </button>
                  </div>
                </form>
              </div>
            )}
          </div>
        )}

        {/* OTP Modal */}
        <OTPModal
          isOpen={isOtpModalOpen}
          onClose={() => setIsOtpModalOpen(false)}
          contactTarget={loginContact}
          purpose="PORTAL_ACCESS_OTP"
          applicationNumber={loginAppNumber}
          onVerified={handleOtpVerified}
        />
      </main>
    </div>
  );
}
