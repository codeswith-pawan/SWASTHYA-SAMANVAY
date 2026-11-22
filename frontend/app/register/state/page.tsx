"use client";

import React, { useState } from "react";
import Link from "next/link";
import {
  Building2,
  MapPin,
  UserCheck,
  FileText,
  CheckCircle2,
  ArrowRight,
  ArrowLeft,
  AlertCircle,
  ShieldCheck,
  Phone,
  Mail,
  Info,
  Clock,
  Check,
  Landmark,
} from "lucide-react";
import { RegistrationNavbar } from "@/components/registration/RegistrationNavbar";
import { OTPModal } from "@/components/registration/OTPModal";
import { DocumentUploader } from "@/components/registration/DocumentUploader";
import { CANONICAL_STATES } from "@/lib/jurisdictions";
import {
  apiCreateStateApplication,
  apiGetMyApplication,
  apiSubmitApplication,
} from "@/lib/api";
import { ApplicantApplication, DocumentType } from "@/lib/types";

const STATE_DOC_SLOTS = [
  {
    type: "GOVERNMENT_ORDER" as DocumentType,
    label: "State Directorate Health Mission Order / Notification",
    description: "Official executive order issued by the Department of Health and Family Welfare.",
    required: true,
  },
  {
    type: "IDENTITY_PROOF" as DocumentType,
    label: "Authorized Signatory Credential",
    description: "Official government identification or departmental accreditation.",
    required: false,
  },
];

export default function RegisterStatePage() {
  const [step, setStep] = useState<1 | 2 | 3 | 4>(1);

  // Form States - Step 1: State Directorate Details
  const [stateDirectorateName, setStateDirectorateName] = useState("");
  const [state, setState] = useState("");
  const [address, setAddress] = useState("");
  const [pincode, setPincode] = useState("");

  // Form States - Step 2: Nodal Officer & Contact
  const [nodalOfficerName, setNodalOfficerName] = useState("");
  const [officialDesignation, setOfficialDesignation] = useState("Director of Health Services");
  const [applicantEmail, setApplicantEmail] = useState("");
  const [applicantPhone, setApplicantPhone] = useState("");
  const [emailVerified, setEmailVerified] = useState(false);

  // OTP Modal State
  const [isOtpModalOpen, setIsOtpModalOpen] = useState(false);

  // Created Draft Application & Token
  const [application, setApplication] = useState<ApplicantApplication | null>(null);
  const [applicantToken, setApplicantToken] = useState<string | null>(null);
  const [trackingToken, setTrackingToken] = useState<string | null>(null);

  // Submission & UI States
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [submissionSuccess, setSubmissionSuccess] = useState<{
    applicationNumber: string;
    trackingToken: string;
  } | null>(null);

  const handleProceedToStep2 = (e: React.FormEvent) => {
    e.preventDefault();
    setError("");

    if (!stateDirectorateName.trim()) {
      setError("Please enter the State Directorate / Department title.");
      return;
    }
    if (!state) {
      setError("Please select the State jurisdiction.");
      return;
    }

    setStep(2);
  };

  const handleCreateDraft = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");

    if (!emailVerified) {
      setIsOtpModalOpen(true);
      return;
    }

    if (!nodalOfficerName.trim() || !applicantEmail.trim() || !applicantPhone.trim()) {
      setError("Please fill in all mandatory contact information.");
      return;
    }

    setLoading(true);

    try {
      const payload = {
        applicant_name: stateDirectorateName.trim(),
        applicant_email: applicantEmail.trim(),
        applicant_phone: applicantPhone.trim(),
        state,
        address: address.trim() || undefined,
        pincode: pincode.trim() || undefined,
        official_designation: officialDesignation.trim() || undefined,
        nodal_officer_name: nodalOfficerName.trim() || undefined,
      };

      const res = await apiCreateStateApplication(payload);
      setApplicantToken(res.applicant_token);
      setTrackingToken(res.tracking_token);

      const appData = await apiGetMyApplication(res.applicant_token);
      setApplication(appData);

      setStep(3);
    } catch (err: any) {
      setError(err.message || "Failed to create state directorate application draft.");
    } finally {
      setLoading(false);
    }
  };

  const refreshApplicationDocuments = async () => {
    if (!applicantToken) return;
    try {
      const refreshed = await apiGetMyApplication(applicantToken);
      setApplication(refreshed);
    } catch {
      // ignore
    }
  };

  const handleProceedToStep4 = () => {
    setError("");
    const docs = application?.documents || [];
    const hasOrder = docs.some((d) => d.document_type === "GOVERNMENT_ORDER");

    if (!hasOrder) {
      setError("Mandatory document missing! Please upload the State Directorate Health Mission Order.");
      return;
    }

    setStep(4);
  };

  const handleFinalSubmit = async () => {
    if (!applicantToken || !application) return;
    setLoading(true);
    setError("");

    try {
      const res = await apiSubmitApplication("Final state submission", applicantToken);
      setSubmissionSuccess({
        applicationNumber: res.application_number,
        trackingToken: res.tracking_token || trackingToken || "",
      });
    } catch (err: any) {
      setError(err.message || "Final submission failed. Please verify requirements.");
    } finally {
      setLoading(false);
    }
  };

  const stepsList = [
    { num: 1, label: "State Directorate", icon: Landmark },
    { num: 2, label: "Directorate & OTP", icon: UserCheck },
    { num: 3, label: "Mission Order", icon: FileText },
    { num: 4, label: "Review & Submit", icon: ShieldCheck },
  ];

  return (
    <div className="min-h-screen bg-[#F4F8FC] text-[#14243B] flex flex-col font-sans">
      <RegistrationNavbar />

      <main className="flex-1 mx-auto w-full max-w-7xl px-4 sm:px-6 lg:px-8 py-8 sm:py-10 space-y-8">
        {/* Breadcrumb & Header Title */}
        <div>
          <nav className="flex items-center gap-2 text-xs font-medium text-slate-500 mb-2">
            <Link href="/" className="hover:text-cyan-700 transition">Portal Home</Link>
            <span>/</span>
            <Link href="/register" className="hover:text-cyan-700 transition">Registration Hub</Link>
            <span>/</span>
            <span className="text-slate-800 font-semibold">State Health Directorate</span>
          </nav>
          <div className="flex flex-wrap items-center justify-between gap-4">
            <div>
              <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-cyan-50 border border-cyan-200 text-cyan-800 text-xs font-semibold mb-2">
                <Landmark className="w-3.5 h-3.5 text-cyan-700" />
                State Executive Tier I Onboarding
              </div>
              <h1 className="text-2xl sm:text-3xl font-extrabold text-slate-900 tracking-tight">
                State Health Directorate Registration
              </h1>
              <p className="text-sm text-slate-600 mt-1 max-w-2xl">
                Register a State Directorate of Health Services to coordinate inter-district medical transfers, specialized triage allocations, and regional critical-care capacity.
              </p>
            </div>
            {application && (
              <div className="flex items-center gap-2 bg-white px-4 py-2 rounded-xl border border-slate-200/80 shadow-sm">
                <span className="text-[11px] font-medium text-slate-500 uppercase">Draft Ref:</span>
                <span className="rounded-lg bg-cyan-50 px-2.5 py-1 text-xs font-mono font-bold text-cyan-800 border border-cyan-200/60">
                  {application.application_number}
                </span>
              </div>
            )}
          </div>
        </div>

        {/* Interactive Step Progress Stepper */}
        {!submissionSuccess && (
          <div className="bg-white/95 backdrop-blur-sm rounded-2xl border border-slate-200/80 p-4 sm:p-5 shadow-[0_4px_20px_rgb(15,23,42,0.04)]">
            <div className="grid grid-cols-4 gap-2 relative">
              {stepsList.map((s, idx) => {
                const isCompleted = step > s.num;
                const isCurrent = step === s.num;
                const IconComponent = s.icon;
                return (
                  <div key={s.num} className="flex flex-col items-center text-center relative z-10">
                    <div
                      className={`flex h-10 w-10 sm:h-11 sm:w-11 items-center justify-center rounded-xl font-bold text-xs sm:text-sm transition-all duration-200 ${
                        isCompleted
                          ? "bg-emerald-500 text-white shadow-md shadow-emerald-500/20"
                          : isCurrent
                          ? "bg-cyan-700 text-white shadow-lg shadow-cyan-700/30 ring-4 ring-cyan-500/15"
                          : "bg-slate-100 text-slate-400 border border-slate-200"
                      }`}
                    >
                      {isCompleted ? <Check className="w-5 h-5 stroke-[2.5]" /> : <IconComponent className="w-5 h-5" />}
                    </div>
                    <span
                      className={`mt-2 text-[11px] sm:text-xs font-semibold tracking-tight transition ${
                        isCurrent
                          ? "text-cyan-800 font-bold"
                          : isCompleted
                          ? "text-emerald-700"
                          : "text-slate-400"
                      }`}
                    >
                      Step {s.num}: {s.label}
                    </span>
                  </div>
                );
              })}
            </div>
          </div>
        )}

        {/* Error Alert */}
        {error && (
          <div className="rounded-2xl border border-rose-200 bg-rose-50/80 p-4 text-xs sm:text-sm text-rose-800 flex items-start gap-3 shadow-sm animate-fade-in-up">
            <AlertCircle className="w-5 h-5 text-rose-600 shrink-0 mt-0.5" />
            <div className="flex-1 font-medium leading-relaxed">{error}</div>
          </div>
        )}

        {submissionSuccess ? (
          /* Submission Success Screen */
          <div className="rounded-3xl border border-emerald-200 bg-white/95 backdrop-blur-sm p-8 sm:p-12 text-center space-y-6 shadow-[0_8px_30px_rgb(15,23,42,0.08)] max-w-2xl mx-auto">
            <div className="mx-auto flex h-16 w-16 items-center justify-center rounded-2xl bg-emerald-100 border border-emerald-200 text-emerald-600 shadow-sm">
              <CheckCircle2 className="w-10 h-10" />
            </div>
            <div>
              <span className="rounded-full bg-emerald-50 px-3.5 py-1 text-xs font-bold text-emerald-700 border border-emerald-200 uppercase tracking-wider">
                State Application Dispatched
              </span>
              <h2 className="mt-3 text-2xl sm:text-3xl font-extrabold text-slate-900">
                Application Submitted for Central National Verification
              </h2>
              <p className="mt-2 text-sm text-slate-600 max-w-lg mx-auto">
                Your State Health Directorate registration has been securely forwarded to the National Central Health Administration for high-level validation and credentialing.
              </p>
            </div>

            <div className="max-w-md mx-auto rounded-2xl border border-slate-200 bg-slate-50 p-5 text-left space-y-3 font-mono">
              <div>
                <span className="text-[10px] text-slate-500 uppercase font-sans font-bold tracking-wider">
                  Official Application Number
                </span>
                <p className="text-base font-bold text-cyan-800 select-all">
                  {submissionSuccess.applicationNumber}
                </p>
              </div>
              <div className="border-t border-slate-200 pt-2.5">
                <span className="text-[10px] text-slate-500 uppercase font-sans font-bold tracking-wider">
                  Secret Tracking Token
                </span>
                <p className="text-xs text-emerald-700 select-all break-all">
                  {submissionSuccess.trackingToken}
                </p>
              </div>
            </div>

            <div className="flex flex-wrap items-center justify-center gap-4 pt-4">
              <Link
                href={`/application/track?app=${encodeURIComponent(
                  submissionSuccess.applicationNumber
                )}&token=${encodeURIComponent(submissionSuccess.trackingToken)}`}
                className="inline-flex items-center gap-2 rounded-xl bg-gradient-to-r from-cyan-700 to-teal-700 px-6 py-3 text-xs sm:text-sm font-bold text-white hover:from-cyan-800 hover:to-teal-800 transition shadow-md shadow-cyan-700/20"
              >
                Track Live Application <ArrowRight className="w-4 h-4" />
              </Link>
              <Link
                href="/application/status"
                className="rounded-xl border border-slate-300 bg-white px-6 py-3 text-xs sm:text-sm font-bold text-slate-700 hover:bg-slate-50 hover:border-slate-400 transition shadow-sm"
              >
                View Full Application Record
              </Link>
            </div>
          </div>
        ) : (
          /* Desktop 2-Column Form Layout */
          <div className="lg:grid lg:grid-cols-12 lg:gap-8 items-start">
            {/* Left 8 Columns: Form Steps */}
            <div className="lg:col-span-8">
              {step === 1 && (
                <form onSubmit={handleProceedToStep2} className="space-y-6">
                  <div className="rounded-2xl border border-slate-200/80 border-t-4 border-t-cyan-700 bg-white/95 backdrop-blur-sm p-6 sm:p-8 space-y-6 shadow-[0_8px_30px_rgb(15,23,42,0.06)]">
                    <div className="flex items-center gap-3 border-b border-slate-100 pb-4">
                      <div className="p-2.5 rounded-xl bg-cyan-50 text-cyan-800">
                        <Landmark className="w-5 h-5" />
                      </div>
                      <div>
                        <h2 className="text-base font-bold text-slate-900">
                          Step 1: State Directorate Details
                        </h2>
                        <p className="text-xs text-slate-500">
                          Specify the official state health department / directorate identity and secretariat location.
                        </p>
                      </div>
                    </div>

                    <div>
                      <label className="block text-xs font-semibold text-slate-700 mb-1">
                        State Department / Directorate Title <span className="text-rose-500">*</span>
                      </label>
                      <input
                        type="text"
                        value={stateDirectorateName}
                        onChange={(e) => setStateDirectorateName(e.target.value)}
                        placeholder="e.g. Directorate of Health Services, Government of Bihar"
                        className="w-full rounded-xl border border-slate-300 bg-slate-50/50 px-3.5 py-2.5 text-xs sm:text-sm text-slate-900 placeholder-slate-400 focus:bg-white focus:border-cyan-700 focus:ring-4 focus:ring-cyan-500/10 outline-none transition-all"
                        required
                      />
                    </div>

                    <div>
                      <label className="block text-xs font-semibold text-slate-700 mb-1">
                        State Jurisdiction <span className="text-rose-500">*</span>
                      </label>
                      <select
                        value={state}
                        onChange={(e) => setState(e.target.value)}
                        className="w-full rounded-xl border border-slate-300 bg-slate-50/50 px-3.5 py-2.5 text-xs sm:text-sm text-slate-900 focus:bg-white focus:border-cyan-700 focus:ring-4 focus:ring-cyan-500/10 outline-none transition-all"
                        required
                      >
                        <option value="">Select State</option>
                        {CANONICAL_STATES.map((s) => (
                          <option key={s} value={s}>
                            {s}
                          </option>
                        ))}
                      </select>
                    </div>

                    <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                      <div className="sm:col-span-2">
                        <label className="block text-xs font-semibold text-slate-700 mb-1">
                          Secretariat / Directorate Address
                        </label>
                        <input
                          type="text"
                          value={address}
                          onChange={(e) => setAddress(e.target.value)}
                          placeholder="e.g. Swasthya Bhawan, Secretariat"
                          className="w-full rounded-xl border border-slate-300 bg-slate-50/50 px-3.5 py-2.5 text-xs sm:text-sm text-slate-900 placeholder-slate-400 focus:bg-white focus:border-cyan-700 focus:ring-4 focus:ring-cyan-500/10 outline-none transition-all"
                        />
                      </div>
                      <div>
                        <label className="block text-xs font-semibold text-slate-700 mb-1">
                          PIN Code
                        </label>
                        <input
                          type="text"
                          maxLength={6}
                          value={pincode}
                          onChange={(e) => setPincode(e.target.value.replace(/\D/g, ""))}
                          placeholder="e.g. 800015"
                          className="w-full rounded-xl border border-slate-300 bg-slate-50/50 px-3.5 py-2.5 text-xs sm:text-sm text-slate-900 placeholder-slate-400 focus:bg-white focus:border-cyan-700 focus:ring-4 focus:ring-cyan-500/10 outline-none transition-all"
                        />
                      </div>
                    </div>
                  </div>

                  <div className="flex justify-end">
                    <button
                      type="submit"
                      className="inline-flex items-center gap-2 rounded-xl bg-gradient-to-r from-cyan-700 to-teal-700 px-6 py-3 text-xs sm:text-sm font-bold text-white hover:from-cyan-800 hover:to-teal-800 transition shadow-md shadow-cyan-700/20"
                    >
                      Proceed to Directorate Contact <ArrowRight className="w-4 h-4" />
                    </button>
                  </div>
                </form>
              )}

              {step === 2 && (
                <form onSubmit={handleCreateDraft} className="space-y-6">
                  <div className="rounded-2xl border border-slate-200/80 border-t-4 border-t-cyan-700 bg-white/95 backdrop-blur-sm p-6 sm:p-8 space-y-6 shadow-[0_8px_30px_rgb(15,23,42,0.06)]">
                    <div className="flex items-center gap-3 border-b border-slate-100 pb-4">
                      <div className="p-2.5 rounded-xl bg-cyan-50 text-cyan-800">
                        <UserCheck className="w-5 h-5" />
                      </div>
                      <div>
                        <h2 className="text-base font-bold text-slate-900">
                          Step 2: State Nodal Officer & Verification Contact
                        </h2>
                        <p className="text-xs text-slate-500">
                          Appoint the State Nodal Officer or Director of Health Services for official administrative authorization.
                        </p>
                      </div>
                    </div>

                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                      <div>
                        <label className="block text-xs font-semibold text-slate-700 mb-1">
                          Designated Officer Name <span className="text-rose-500">*</span>
                        </label>
                        <input
                          type="text"
                          value={nodalOfficerName}
                          onChange={(e) => setNodalOfficerName(e.target.value)}
                          placeholder="e.g. Dr. Sudhir Prasad"
                          className="w-full rounded-xl border border-slate-300 bg-slate-50/50 px-3.5 py-2.5 text-xs sm:text-sm text-slate-900 placeholder-slate-400 focus:bg-white focus:border-cyan-700 focus:ring-4 focus:ring-cyan-500/10 outline-none transition-all"
                          required
                        />
                      </div>
                      <div>
                        <label className="block text-xs font-semibold text-slate-700 mb-1">
                          Official Designation <span className="text-rose-500">*</span>
                        </label>
                        <input
                          type="text"
                          value={officialDesignation}
                          onChange={(e) => setOfficialDesignation(e.target.value)}
                          placeholder="e.g. Director of Health Services / State Nodal Officer"
                          className="w-full rounded-xl border border-slate-300 bg-slate-50/50 px-3.5 py-2.5 text-xs sm:text-sm text-slate-900 placeholder-slate-400 focus:bg-white focus:border-cyan-700 focus:ring-4 focus:ring-cyan-500/10 outline-none transition-all"
                          required
                        />
                      </div>
                    </div>

                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                      <div>
                        <label className="block text-xs font-semibold text-slate-700 mb-1">
                          Official Government Email <span className="text-rose-500">*</span>
                        </label>
                        <div className="flex gap-2">
                          <input
                            type="email"
                            value={applicantEmail}
                            onChange={(e) => {
                              setApplicantEmail(e.target.value);
                              setEmailVerified(false);
                            }}
                            placeholder="e.g. director.health@bihar.gov.in"
                            className="flex-1 rounded-xl border border-slate-300 bg-slate-50/50 px-3.5 py-2.5 text-xs sm:text-sm text-slate-900 placeholder-slate-400 focus:bg-white focus:border-cyan-700 focus:ring-4 focus:ring-cyan-500/10 outline-none transition-all"
                            required
                          />
                          <button
                            type="button"
                            onClick={() => {
                              if (!applicantEmail.includes("@")) {
                                setError("Please enter a valid email address.");
                                return;
                              }
                              setIsOtpModalOpen(true);
                            }}
                            className={`rounded-xl px-4 py-2 text-xs font-bold transition shadow-sm ${
                              emailVerified
                                ? "bg-emerald-50 text-emerald-700 border border-emerald-300"
                                : "bg-cyan-700 text-white hover:bg-cyan-800"
                            }`}
                          >
                            {emailVerified ? "✓ Verified" : "Verify Email"}
                          </button>
                        </div>
                        {emailVerified && (
                          <p className="mt-1.5 text-xs text-emerald-600 font-medium flex items-center gap-1">
                            <CheckCircle2 className="w-3.5 h-3.5" />
                            Email ownership confirmed via OTP verification
                          </p>
                        )}
                      </div>

                      <div>
                        <label className="block text-xs font-semibold text-slate-700 mb-1">
                          Official Contact Phone <span className="text-rose-500">*</span>
                        </label>
                        <input
                          type="tel"
                          value={applicantPhone}
                          onChange={(e) => setApplicantPhone(e.target.value)}
                          placeholder="e.g. +91 94310 12345"
                          className="w-full rounded-xl border border-slate-300 bg-slate-50/50 px-3.5 py-2.5 text-xs sm:text-sm text-slate-900 placeholder-slate-400 focus:bg-white focus:border-cyan-700 focus:ring-4 focus:ring-cyan-500/10 outline-none transition-all"
                          required
                        />
                      </div>
                    </div>
                  </div>

                  <div className="flex justify-between items-center">
                    <button
                      type="button"
                      onClick={() => setStep(1)}
                      className="inline-flex items-center gap-2 rounded-xl border border-slate-300 bg-white px-5 py-2.5 text-xs sm:text-sm font-semibold text-slate-700 hover:bg-slate-50 transition shadow-sm"
                    >
                      <ArrowLeft className="w-4 h-4" /> Back to State Details
                    </button>

                    <button
                      type="submit"
                      disabled={loading || !emailVerified}
                      className="inline-flex items-center gap-2 rounded-xl bg-gradient-to-r from-cyan-700 to-teal-700 px-6 py-3 text-xs sm:text-sm font-bold text-white hover:from-cyan-800 hover:to-teal-800 disabled:opacity-50 transition shadow-md shadow-cyan-700/20"
                    >
                      {loading ? "Creating Draft..." : "Save Draft & Proceed to Documents"}
                      <ArrowRight className="w-4 h-4" />
                    </button>
                  </div>
                </form>
              )}

              {step === 3 && (
                <div className="space-y-6">
                  <div className="rounded-2xl border border-slate-200/80 border-t-4 border-t-cyan-700 bg-white/95 backdrop-blur-sm p-6 sm:p-8 space-y-6 shadow-[0_8px_30px_rgb(15,23,42,0.06)]">
                    <div className="flex items-center gap-3 border-b border-slate-100 pb-4">
                      <div className="p-2.5 rounded-xl bg-cyan-50 text-cyan-800">
                        <FileText className="w-5 h-5" />
                      </div>
                      <div>
                        <h2 className="text-base font-bold text-slate-900">
                          Step 3: Upload State Directorate Health Mission Order
                        </h2>
                        <p className="text-xs text-slate-500">
                          Upload the executive order or gazetted notification issued by the Department of Health and Family Welfare authorizing state-level network administration.
                        </p>
                      </div>
                    </div>

                    <DocumentUploader
                      slots={STATE_DOC_SLOTS}
                      existingDocuments={application?.documents || []}
                      applicantToken={applicantToken}
                      canEdit={true}
                      onDocumentsChanged={refreshApplicationDocuments}
                    />
                  </div>

                  <div className="flex justify-between items-center">
                    <button
                      type="button"
                      onClick={() => setStep(2)}
                      className="inline-flex items-center gap-2 rounded-xl border border-slate-300 bg-white px-5 py-2.5 text-xs sm:text-sm font-semibold text-slate-700 hover:bg-slate-50 transition shadow-sm"
                    >
                      <ArrowLeft className="w-4 h-4" /> Back to Contact
                    </button>

                    <button
                      type="button"
                      onClick={handleProceedToStep4}
                      className="inline-flex items-center gap-2 rounded-xl bg-gradient-to-r from-cyan-700 to-teal-700 px-6 py-3 text-xs sm:text-sm font-bold text-white hover:from-cyan-800 hover:to-teal-800 transition shadow-md shadow-cyan-700/20"
                    >
                      Review Application Summary <ArrowRight className="w-4 h-4" />
                    </button>
                  </div>
                </div>
              )}

              {step === 4 && (
                <div className="space-y-6">
                  <div className="rounded-2xl border border-slate-200/80 border-t-4 border-t-cyan-700 bg-white/95 backdrop-blur-sm p-6 sm:p-8 space-y-6 shadow-[0_8px_30px_rgb(15,23,42,0.06)]">
                    <div className="border-b border-slate-100 pb-4">
                      <span className="rounded-full bg-cyan-50 px-3 py-1 text-xs font-bold text-cyan-800 border border-cyan-200 uppercase tracking-wider">
                        State Application Final Review
                      </span>
                      <h2 className="mt-3 text-xl sm:text-2xl font-bold text-slate-900">{stateDirectorateName}</h2>
                      <p className="text-xs sm:text-sm text-slate-500">
                        State Jurisdiction: {state}
                      </p>
                    </div>

                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 text-xs">
                      <div className="rounded-xl border border-slate-200 bg-slate-50/70 p-4 space-y-2">
                        <h4 className="font-bold text-slate-800 uppercase tracking-wider text-[11px]">
                          State Nodal Authority
                        </h4>
                        <p className="text-slate-600">Officer: <strong className="text-slate-900">{nodalOfficerName}</strong></p>
                        <p className="text-slate-600">Designation: <strong className="text-slate-900">{officialDesignation}</strong></p>
                        <p className="text-slate-600">Secretariat: <strong className="text-slate-900">{address || "N/A"}</strong></p>
                      </div>

                      <div className="rounded-xl border border-slate-200 bg-slate-50/70 p-4 space-y-2">
                        <h4 className="font-bold text-slate-800 uppercase tracking-wider text-[11px]">
                          Verified Contact Details
                        </h4>
                        <p className="text-slate-600">Official Email: <strong className="text-slate-900">{applicantEmail}</strong></p>
                        <p className="text-slate-600">Official Phone: <strong className="text-slate-900">{applicantPhone}</strong></p>
                        <p className="text-slate-600">Attached Documents: <strong className="text-slate-900">{application?.documents.length || 0} File(s)</strong></p>
                      </div>
                    </div>

                    <div className="rounded-xl border border-cyan-200 bg-cyan-50/60 p-4 text-xs text-cyan-950">
                      <p className="font-bold text-slate-900">Statutory Legal Declaration:</p>
                      <p className="text-[11px] text-slate-600 mt-1 leading-relaxed">
                        I hereby declare that this onboarding application is submitted under official executive authorization on behalf of the State Directorate of Health Services under the Department of Health and Family Welfare.
                      </p>
                    </div>
                  </div>

                  <div className="flex justify-between items-center">
                    <button
                      type="button"
                      onClick={() => setStep(3)}
                      className="inline-flex items-center gap-2 rounded-xl border border-slate-300 bg-white px-5 py-2.5 text-xs sm:text-sm font-semibold text-slate-700 hover:bg-slate-50 transition shadow-sm"
                    >
                      <ArrowLeft className="w-4 h-4" /> Back to Documents
                    </button>

                    <button
                      type="button"
                      disabled={loading}
                      onClick={handleFinalSubmit}
                      className="inline-flex items-center gap-2 rounded-xl bg-gradient-to-r from-emerald-600 to-teal-600 px-8 py-3.5 text-xs sm:text-sm font-bold text-white hover:from-emerald-700 hover:to-teal-700 disabled:opacity-50 transition shadow-lg shadow-emerald-600/20"
                    >
                      {loading ? "Submitting Application..." : "Final Submit Application ✓"}
                    </button>
                  </div>
                </div>
              )}
            </div>

            {/* Right 4 Columns: Sticky State Authority Guidance Card */}
            <div className="hidden lg:block lg:col-span-4 space-y-5">
              <div className="sticky top-24 space-y-5">
                {/* State Authority Mandate Card */}
                <div className="bg-white/95 backdrop-blur-sm rounded-2xl border border-slate-200/80 p-5 shadow-[0_8px_30px_rgb(15,23,42,0.06)] space-y-4">
                  <div className="flex items-center gap-2.5 border-b border-slate-100 pb-3">
                    <div className="p-2 rounded-lg bg-cyan-50 text-cyan-800">
                      <ShieldCheck className="w-4 h-4" />
                    </div>
                    <div>
                      <h3 className="text-xs font-bold text-slate-900 uppercase tracking-wider">
                        State Authority Mandate
                      </h3>
                      <p className="text-[11px] text-slate-500">Tier I Regional Oversight</p>
                    </div>
                  </div>

                  <ul className="space-y-2.5 text-xs text-slate-600">
                    <li className="flex items-start gap-2">
                      <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0 mt-0.5" />
                      <span>Oversee District Health Authority onboarding across all constituent districts.</span>
                    </li>
                    <li className="flex items-start gap-2">
                      <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0 mt-0.5" />
                      <span>Coordinate inter-district referral protocols during mass casualty surges.</span>
                    </li>
                    <li className="flex items-start gap-2">
                      <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0 mt-0.5" />
                      <span>Enforce clinical SLA standards and ambulance dispatch turnaround targets.</span>
                    </li>
                    <li className="flex items-start gap-2">
                      <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0 mt-0.5" />
                      <span>Direct integration with National Emergency Medical Relief Command.</span>
                    </li>
                  </ul>
                </div>

                {/* Central Approval Path Card */}
                <div className="bg-white/95 backdrop-blur-sm rounded-2xl border border-slate-200/80 p-5 shadow-[0_8px_30px_rgb(15,23,42,0.06)] space-y-3">
                  <div className="flex items-center gap-2 text-xs font-bold text-slate-900 uppercase tracking-wider border-b border-slate-100 pb-2">
                    <Clock className="w-4 h-4 text-cyan-700" />
                    Central Approval Path
                  </div>
                  <div className="space-y-2 text-xs">
                    <div className="flex items-center justify-between text-slate-600">
                      <span>1. Application Submission</span>
                      <span className="font-semibold text-emerald-700">Instant</span>
                    </div>
                    <div className="flex items-center justify-between text-slate-600">
                      <span>2. National Ministry Clearance</span>
                      <span className="font-semibold text-cyan-800">24 – 48 Hours</span>
                    </div>
                    <div className="flex items-center justify-between text-slate-600">
                      <span>3. Executive Credential Provisioning</span>
                      <span className="font-semibold text-teal-700">Via Official Email</span>
                    </div>
                  </div>
                </div>

                {/* Support Desk Card */}
                <div className="bg-gradient-to-br from-cyan-50 to-slate-50 rounded-2xl border border-cyan-200/70 p-5 space-y-2 text-xs">
                  <span className="font-bold text-slate-900 block">State Technical Coordination</span>
                  <p className="text-slate-600 leading-relaxed text-[11px]">
                    For inter-state protocols or health mission order assistance:
                  </p>
                  <a
                    href="mailto:pawanbussiness108@gmail.com"
                    className="inline-flex items-center gap-1.5 font-semibold text-cyan-800 hover:text-cyan-900 transition"
                  >
                    <Mail className="w-3.5 h-3.5" /> pawanbussiness108@gmail.com
                  </a>
                </div>
              </div>
            </div>
          </div>
        )}

        <OTPModal
          isOpen={isOtpModalOpen}
          onClose={() => setIsOtpModalOpen(false)}
          contactTarget={applicantEmail}
          purpose="REGISTRATION_OTP"
          onVerified={() => {
            setEmailVerified(true);
            setIsOtpModalOpen(false);
          }}
        />
      </main>
    </div>
  );
}
