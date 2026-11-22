"use client";

import React, { useState } from "react";
import Link from "next/link";
import {
  Hospital,
  Building2,
  ShieldCheck,
  CheckCircle2,
  ArrowRight,
  Shield,
  FileCheck2,
  Search,
  Lock,
  Mail,
  Phone,
  Clock,
  HelpCircle,
  FileText,
  MapPin,
  ChevronRight,
  AlertCircle,
  UserCheck,
} from "lucide-react";
import { RegistrationNavbar } from "@/components/registration/RegistrationNavbar";
import { OTPModal } from "@/components/registration/OTPModal";
import { DocumentUploader } from "@/components/registration/DocumentUploader";
import { CANONICAL_STATES, getDistrictsForState } from "@/lib/jurisdictions";
import {
  apiCreateHospitalApplication,
  apiGetMyApplication,
  apiSubmitApplication,
} from "@/lib/api";
import { ApplicantApplication, DocumentType } from "@/lib/types";

const HOSPITAL_DOC_SLOTS = [
  {
    type: "CLINICAL_LICENSE" as DocumentType,
    label: "Clinical Establishment Registration",
    description: "Valid certificate under Clinical Establishments (Registration and Regulation) Act.",
    required: true,
  },
  {
    type: "FIRE_SAFETY_NOC" as DocumentType,
    label: "Fire Safety NOC Clearance",
    description: "Fire department safety compliance and clearance certificate.",
    required: true,
  },
  {
    type: "POLLUTION_CONTROL_NOC" as DocumentType,
    label: "Bio-Medical Waste & Pollution Control NOC",
    description: "State Pollution Control Board authorization for bio-medical waste management.",
    required: false,
  },
  {
    type: "MEDICAL_COUNCIL_AFFILIATION" as DocumentType,
    label: "Medical Council Affiliation / Accreditation",
    description: "NMC / NABH / NABL certificate or university teaching hospital affiliation.",
    required: false,
  },
];

export default function RegisterHospitalPage() {
  const [step, setStep] = useState<1 | 2 | 3 | 4>(1);

  // Form States - Step 1: Facility Profile & Capacity
  const [facilityName, setFacilityName] = useState("");
  const [state, setState] = useState("");
  const [district, setDistrict] = useState("");
  const [city, setCity] = useState("");
  const [address, setAddress] = useState("");
  const [pincode, setPincode] = useState("");
  const [totalBeds, setTotalBeds] = useState<number>(100);
  const [icuBeds, setIcuBeds] = useState<number>(20);
  const [emergencyBeds, setEmergencyBeds] = useState<number>(15);
  const [ventilatorCount, setVentilatorCount] = useState<number>(10);
  const [emergency24x7, setEmergency24x7] = useState<boolean>(true);
  const [latitude, setLatitude] = useState<number>(31.634);
  const [longitude, setLongitude] = useState<number>(74.8723);

  // Form States - Step 2: Nodal Officer & Contact
  const [nodalOfficerName, setNodalOfficerName] = useState("");
  const [officialDesignation, setOfficialDesignation] = useState("Medical Superintendent");
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

  const districts = state ? getDistrictsForState(state) : [];

  // Step 1 Validation -> Proceed to Step 2
  const handleProceedToStep2 = (e: React.FormEvent) => {
    e.preventDefault();
    setError("");

    if (!facilityName.trim()) {
      setError("Please enter the official hospital or facility name.");
      return;
    }
    if (!state || !district) {
      setError("Please select both State and District jurisdictions.");
      return;
    }
    if (totalBeds < 1 || icuBeds < 0) {
      setError("Please enter valid bed capacities.");
      return;
    }
    if (icuBeds > totalBeds) {
      setError("ICU beds cannot exceed total bed capacity.");
      return;
    }

    setStep(2);
  };

  // Step 2 Validation -> Create Draft Application on Backend
  const handleCreateDraft = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");

    if (!nodalOfficerName.trim()) {
      setError("Please provide the designated Nodal Officer's full name.");
      return;
    }
    if (!applicantEmail.trim() || !applicantEmail.includes("@")) {
      setError("Please provide a valid official email address.");
      return;
    }
    if (!emailVerified) {
      setError("Please verify the official email address via OTP before proceeding.");
      return;
    }

    setLoading(true);

    try {
      const res = await apiCreateHospitalApplication({
        applicant_name: facilityName.trim(),
        state,
        district,
        city: city.trim() || undefined,
        address: address.trim() || undefined,
        pincode: pincode.trim() || undefined,
        nodal_officer_name: nodalOfficerName.trim() || undefined,
        official_designation: officialDesignation.trim() || undefined,
        applicant_email: applicantEmail.trim(),
        applicant_phone: applicantPhone.trim(),
        profile_data: {
          total_beds: totalBeds,
          icu_beds: icuBeds,
          emergency_beds: emergencyBeds,
          ventilator_count: ventilatorCount,
          emergency_24x7: emergency24x7,
          latitude,
          longitude,
        },
      });

      setApplicantToken(res.applicant_token);
      setTrackingToken(res.tracking_token);

      const appData = await apiGetMyApplication(res.applicant_token);
      setApplication(appData);
      setStep(3);
    } catch (err: any) {
      setError(err.message || "Failed to create hospital application draft. Please check your inputs.");
    } finally {
      setLoading(false);
    }
  };

  // Refresh Application Documents after upload/delete
  const refreshApplicationDocuments = async () => {
    if (!applicantToken) return;
    try {
      const updated = await apiGetMyApplication(applicantToken);
      setApplication(updated);
    } catch {
      // Ignore background refresh errors
    }
  };

  // Step 3 Validation -> Proceed to Step 4
  const handleProceedToStep4 = () => {
    setError("");

    const uploadedTypes = (application?.documents || []).map((d) => d.document_type);
    const missingRequired = HOSPITAL_DOC_SLOTS.filter(
      (slot) => slot.required && !uploadedTypes.includes(slot.type)
    );

    if (missingRequired.length > 0) {
      setError(
        `Please upload all required compliance documents: ${missingRequired
          .map((m) => m.label)
          .join(", ")}`
      );
      return;
    }

    setStep(4);
  };

  // Step 4: Final Submit Application
  const handleFinalSubmit = async () => {
    if (!applicantToken || !application) return;
    setLoading(true);
    setError("");

    try {
      const res = await apiSubmitApplication("Final hospital submission", applicantToken);
      setSubmissionSuccess({
        applicationNumber: res.application_number,
        trackingToken: res.tracking_token || trackingToken || "",
      });
    } catch (err: any) {
      setError(err.message || "Final submission failed. Please ensure all requirements are met.");
    } finally {
      setLoading(false);
    }
  };

  const steps = [
    { num: 1, title: "Facility Profile", desc: "Capacity & GPS" },
    { num: 2, title: "Nodal Officer", desc: "Contact & 2FA" },
    { num: 3, title: "Documents", desc: "Upload Compliance" },
    { num: 4, title: "Final Review", desc: "Declaration & Submit" },
  ];

  return (
    <div className="min-h-screen bg-[#F4F8FC] text-[#14243B] flex flex-col font-sans">
      <RegistrationNavbar />

      <main className="flex-1 mx-auto w-full max-w-7xl px-4 sm:px-6 py-8 sm:py-10 space-y-8">
        {/* Breadcrumb & Title */}
        <div className="animate-fade-in-up">
          <div className="flex items-center gap-2 text-xs text-slate-500 font-medium">
            <Link href="/" className="hover:text-teal-900 transition">Home</Link>
            <ChevronRight className="w-3.5 h-3.5 text-slate-400" />
            <Link href="/register" className="hover:text-teal-900 transition">Registration Hub</Link>
            <ChevronRight className="w-3.5 h-3.5 text-slate-400" />
            <span className="text-slate-800 font-semibold">Hospital Facility</span>
          </div>

          <div className="mt-2.5 flex flex-wrap items-center justify-between gap-4">
            <div>
              <h1 className="text-2xl sm:text-3xl font-extrabold tracking-tight text-slate-900">
                Hospital Onboarding & Accreditation
              </h1>
              <p className="text-xs sm:text-sm text-slate-600 mt-1">
                Accredit your medical facility to onboard inpatient beds, ICU inventory, and emergency transfers into ArogyaSetu Grid.
              </p>
            </div>
            {application && (
              <span className="rounded-full bg-teal-50 border border-teal-300 px-3.5 py-1 text-xs font-mono font-bold text-teal-900 shadow-2xs">
                Ref: {application.application_number}
              </span>
            )}
          </div>
        </div>

        {/* Interactive Pill Stepper */}
        {!submissionSuccess && (
          <div className="rounded-2xl border border-slate-200/80 bg-white/95 backdrop-blur-sm p-4 sm:p-5 shadow-[0_4px_20px_rgb(15,23,42,0.04)] animate-fade-in-up">
            <div className="grid grid-cols-2 md:grid-cols-4 gap-3 sm:gap-4">
              {steps.map((s) => {
                const isCurrent = step === s.num;
                const isCompleted = step > s.num;

                return (
                  <div
                    key={s.num}
                    className={`flex items-center gap-3 p-2.5 rounded-xl transition ${
                      isCurrent
                        ? "bg-teal-50 border border-teal-300 shadow-xs"
                        : isCompleted
                        ? "bg-slate-50/70 border border-slate-200"
                        : "opacity-60"
                    }`}
                  >
                    <div
                      className={`flex h-8 w-8 items-center justify-center rounded-full text-xs font-bold shrink-0 transition ${
                        isCurrent
                          ? "bg-teal-600 text-white shadow-md shadow-teal-600/30 ring-2 ring-teal-400/50"
                          : isCompleted
                          ? "bg-emerald-600 text-white"
                          : "bg-slate-200 text-slate-600"
                      }`}
                    >
                      {isCompleted ? "✓" : s.num}
                    </div>
                    <div className="min-w-0">
                      <p
                        className={`text-xs font-bold truncate ${
                          isCurrent ? "text-teal-950 font-extrabold" : "text-slate-800"
                        }`}
                      >
                        {s.title}
                      </p>
                      <p className="text-[10px] text-slate-500 truncate hidden sm:block">
                        {s.desc}
                      </p>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        )}

        {/* Global Error Notice */}
        {error && (
          <div className="rounded-2xl border border-rose-200 bg-rose-50 p-4 text-xs text-rose-800 flex items-start gap-3 shadow-2xs animate-fade-in-up">
            <AlertCircle className="w-5 h-5 text-rose-600 shrink-0 mt-0.5" />
            <div className="flex-1 font-medium">{error}</div>
          </div>
        )}

        {/* SUCCESS CONFIRMATION VIEW */}
        {submissionSuccess ? (
          <div className="rounded-3xl border border-slate-200/90 border-t-4 border-t-emerald-600 bg-white/95 backdrop-blur-sm p-8 sm:p-12 text-center space-y-6 shadow-[0_12px_40px_rgb(15,23,42,0.08)] animate-fade-in-up">
            <div className="mx-auto flex h-16 w-16 items-center justify-center rounded-2xl bg-emerald-50 border border-emerald-200 text-3xl text-emerald-600 shadow-xs">
              ✓
            </div>
            <div className="space-y-2">
              <span className="rounded-full bg-emerald-50 border border-emerald-300 px-3.5 py-1 text-xs font-bold text-emerald-800 uppercase tracking-wider">
                Application Successfully Submitted
              </span>
              <h2 className="text-2xl sm:text-3xl font-extrabold text-slate-900">
                Application Submitted for District Verification
              </h2>
              <p className="text-xs sm:text-sm text-slate-600 max-w-lg mx-auto leading-relaxed">
                Your hospital onboarding application is now active in the government verification pipeline. Save your Application Number and Secret Tracking Token below to track real-time milestones.
              </p>
            </div>

            {/* Reference Credentials Box */}
            <div className="max-w-md mx-auto rounded-2xl border border-slate-200 bg-slate-50/80 p-5 text-left space-y-3 font-mono shadow-2xs">
              <div>
                <span className="text-[10px] text-slate-500 uppercase font-sans font-bold">
                  Official Application Number
                </span>
                <p className="text-lg font-bold text-teal-800 select-all">
                  {submissionSuccess.applicationNumber}
                </p>
              </div>
              <div className="border-t border-slate-200 pt-2.5">
                <span className="text-[10px] text-slate-500 uppercase font-sans font-bold">
                  Secret Tracking Token
                </span>
                <p className="text-xs text-emerald-700 select-all break-all font-semibold">
                  {submissionSuccess.trackingToken}
                </p>
              </div>
            </div>

            <div className="flex flex-wrap items-center justify-center gap-4 pt-4">
              <Link
                href={`/application/track?app=${encodeURIComponent(
                  submissionSuccess.applicationNumber
                )}&token=${encodeURIComponent(submissionSuccess.trackingToken)}`}
                className="rounded-xl bg-gradient-to-r from-teal-600 to-emerald-600 px-6 py-3 text-xs font-bold text-white hover:from-teal-700 hover:to-emerald-700 transition shadow-md shadow-teal-600/20 btn-hover-lift"
              >
                Track Live Application →
              </Link>
              <Link
                href="/application/status"
                className="rounded-xl border border-slate-300 bg-white px-6 py-3 text-xs font-bold text-slate-700 hover:bg-slate-50 transition shadow-2xs btn-hover-lift"
              >
                View Full Applicant Record
              </Link>
            </div>
          </div>
        ) : (
          /* Desktop 2-Column Layout */
          <div className="lg:grid lg:grid-cols-12 lg:gap-8 items-start">
            {/* Main Form Cards Column */}
            <div className="lg:col-span-8 space-y-6">
              {/* STEP 1: FACILITY PROFILE & CAPACITY */}
              {step === 1 && (
                <form onSubmit={handleProceedToStep2} className="space-y-6">
                  {/* Card 1: Facility Details */}
                  <div className="rounded-2xl border border-slate-200/90 border-t-4 border-t-teal-600 bg-white/95 backdrop-blur-sm p-6 sm:p-8 space-y-6 shadow-[0_8px_30px_rgb(15,23,42,0.06)]">
                    <div className="flex items-center gap-3 pb-2 border-b border-slate-100">
                      <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-teal-50 border border-teal-200 text-teal-700">
                        <Hospital className="w-5 h-5" />
                      </div>
                      <div>
                        <h3 className="text-base font-bold text-slate-900">
                          Hospital Facility Profile
                        </h3>
                        <p className="text-[11px] text-slate-500">
                          Legal facility name and geographical jurisdiction
                        </p>
                      </div>
                    </div>

                    <div className="space-y-4">
                      <div>
                        <label className="block text-xs font-semibold text-slate-700">
                          Official Hospital / Facility Name *
                        </label>
                        <input
                          type="text"
                          value={facilityName}
                          onChange={(e) => setFacilityName(e.target.value)}
                          placeholder="e.g. Guru Nanak Dev Hospital & Medical Research Centre"
                          className="mt-1.5 w-full rounded-xl border border-slate-300 bg-slate-50/50 px-3.5 py-2.5 text-xs text-slate-900 placeholder-slate-400 outline-none focus:bg-white focus:border-teal-600 focus:ring-4 focus:ring-teal-500/10 transition shadow-2xs"
                          required
                        />
                      </div>

                      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                        <div>
                          <label className="block text-xs font-semibold text-slate-700">
                            State Jurisdiction *
                          </label>
                          <select
                            value={state}
                            onChange={(e) => {
                              setState(e.target.value);
                              setDistrict("");
                            }}
                            className="mt-1.5 w-full rounded-xl border border-slate-300 bg-slate-50/50 px-3.5 py-2.5 text-xs text-slate-900 outline-none focus:bg-white focus:border-teal-600 focus:ring-4 focus:ring-teal-500/10 transition shadow-2xs"
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

                        <div>
                          <label className="block text-xs font-semibold text-slate-700">
                            District Jurisdiction *
                          </label>
                          <select
                            value={district}
                            onChange={(e) => setDistrict(e.target.value)}
                            disabled={!state}
                            className="mt-1.5 w-full rounded-xl border border-slate-300 bg-slate-50/50 px-3.5 py-2.5 text-xs text-slate-900 outline-none focus:bg-white focus:border-teal-600 focus:ring-4 focus:ring-teal-500/10 transition shadow-2xs disabled:opacity-50"
                            required
                          >
                            <option value="">
                              {state ? "Select District" : "Select State First"}
                            </option>
                            {districts.map((d) => (
                              <option key={d} value={d}>
                                {d}
                              </option>
                            ))}
                          </select>
                        </div>
                      </div>

                      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                        <div>
                          <label className="block text-xs font-semibold text-slate-700">City / Town</label>
                          <input
                            type="text"
                            value={city}
                            onChange={(e) => setCity(e.target.value)}
                            placeholder="e.g. Amritsar"
                            className="mt-1.5 w-full rounded-xl border border-slate-300 bg-slate-50/50 px-3.5 py-2.5 text-xs text-slate-900 placeholder-slate-400 outline-none focus:bg-white focus:border-teal-600 focus:ring-4 focus:ring-teal-500/10 transition shadow-2xs"
                          />
                        </div>
                        <div className="sm:col-span-2">
                          <label className="block text-xs font-semibold text-slate-700">Street Address</label>
                          <input
                            type="text"
                            value={address}
                            onChange={(e) => setAddress(e.target.value)}
                            placeholder="e.g. Majitha Road, Medical Enclave"
                            className="mt-1.5 w-full rounded-xl border border-slate-300 bg-slate-50/50 px-3.5 py-2.5 text-xs text-slate-900 placeholder-slate-400 outline-none focus:bg-white focus:border-teal-600 focus:ring-4 focus:ring-teal-500/10 transition shadow-2xs"
                          />
                        </div>
                      </div>

                      <div className="w-full sm:w-1/3">
                        <label className="block text-xs font-semibold text-slate-700">PIN Code</label>
                        <input
                          type="text"
                          maxLength={6}
                          value={pincode}
                          onChange={(e) => setPincode(e.target.value.replace(/\D/g, ""))}
                          placeholder="e.g. 143001"
                          className="mt-1.5 w-full rounded-xl border border-slate-300 bg-slate-50/50 px-3.5 py-2.5 text-xs text-slate-900 placeholder-slate-400 outline-none focus:bg-white focus:border-teal-600 focus:ring-4 focus:ring-teal-500/10 transition shadow-2xs"
                        />
                      </div>
                    </div>
                  </div>

                  {/* Card 2: Bed Capacity & Logistics */}
                  <div className="rounded-2xl border border-slate-200/90 border-t-4 border-t-emerald-600 bg-white/95 backdrop-blur-sm p-6 sm:p-8 space-y-6 shadow-[0_8px_30px_rgb(15,23,42,0.06)]">
                    <div className="flex items-center gap-3 pb-2 border-b border-slate-100">
                      <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-emerald-50 border border-emerald-200 text-emerald-700">
                        <FileCheck2 className="w-5 h-5" />
                      </div>
                      <div>
                        <h3 className="text-base font-bold text-slate-900">
                          Clinical Bed & Critical Care Capacity
                        </h3>
                        <p className="text-[11px] text-slate-500">
                          Inpatient quotas and emergency ventilator equipment
                        </p>
                      </div>
                    </div>

                    <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
                      <div>
                        <label className="block text-xs font-semibold text-slate-700">Total Inpatient Beds *</label>
                        <input
                          type="number"
                          min={1}
                          value={totalBeds}
                          onChange={(e) => setTotalBeds(Number(e.target.value))}
                          className="mt-1.5 w-full rounded-xl border border-slate-300 bg-slate-50/50 px-3.5 py-2.5 text-xs text-slate-900 outline-none focus:bg-white focus:border-teal-600 focus:ring-4 focus:ring-teal-500/10 transition shadow-2xs"
                          required
                        />
                      </div>
                      <div>
                        <label className="block text-xs font-semibold text-slate-700">ICU Beds *</label>
                        <input
                          type="number"
                          min={0}
                          value={icuBeds}
                          onChange={(e) => setIcuBeds(Number(e.target.value))}
                          className="mt-1.5 w-full rounded-xl border border-slate-300 bg-slate-50/50 px-3.5 py-2.5 text-xs text-slate-900 outline-none focus:bg-white focus:border-teal-600 focus:ring-4 focus:ring-teal-500/10 transition shadow-2xs"
                          required
                        />
                      </div>
                      <div>
                        <label className="block text-xs font-semibold text-slate-700">Emergency Beds</label>
                        <input
                          type="number"
                          min={0}
                          value={emergencyBeds}
                          onChange={(e) => setEmergencyBeds(Number(e.target.value))}
                          className="mt-1.5 w-full rounded-xl border border-slate-300 bg-slate-50/50 px-3.5 py-2.5 text-xs text-slate-900 outline-none focus:bg-white focus:border-teal-600 focus:ring-4 focus:ring-teal-500/10 transition shadow-2xs"
                        />
                      </div>
                      <div>
                        <label className="block text-xs font-semibold text-slate-700">Ventilators</label>
                        <input
                          type="number"
                          min={0}
                          value={ventilatorCount}
                          onChange={(e) => setVentilatorCount(Number(e.target.value))}
                          className="mt-1.5 w-full rounded-xl border border-slate-300 bg-slate-50/50 px-3.5 py-2.5 text-xs text-slate-900 outline-none focus:bg-white focus:border-teal-600 focus:ring-4 focus:ring-teal-500/10 transition shadow-2xs"
                        />
                      </div>
                    </div>

                    <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 pt-2">
                      <div className="flex items-center gap-3">
                        <input
                          type="checkbox"
                          id="emergency24x7"
                          checked={emergency24x7}
                          onChange={(e) => setEmergency24x7(e.target.checked)}
                          className="h-4 w-4 rounded border-slate-300 text-teal-600 focus:ring-teal-500"
                        />
                        <label htmlFor="emergency24x7" className="text-xs font-semibold text-slate-800">
                          24x7 Emergency Casualty Unit
                        </label>
                      </div>
                      <div>
                        <label className="block text-xs font-semibold text-slate-700">Latitude (GPS)</label>
                        <input
                          type="number"
                          step="0.0001"
                          value={latitude}
                          onChange={(e) => setLatitude(Number(e.target.value))}
                          className="mt-1 w-full rounded-xl border border-slate-300 bg-slate-50/50 px-3 py-2 text-xs text-slate-900 outline-none focus:bg-white focus:border-teal-600 transition shadow-2xs"
                        />
                      </div>
                      <div>
                        <label className="block text-xs font-semibold text-slate-700">Longitude (GPS)</label>
                        <input
                          type="number"
                          step="0.0001"
                          value={longitude}
                          onChange={(e) => setLongitude(Number(e.target.value))}
                          className="mt-1 w-full rounded-xl border border-slate-300 bg-slate-50/50 px-3 py-2 text-xs text-slate-900 outline-none focus:bg-white focus:border-teal-600 transition shadow-2xs"
                        />
                      </div>
                    </div>
                  </div>

                  <div className="flex justify-end pt-2">
                    <button
                      type="submit"
                      className="rounded-xl bg-gradient-to-r from-teal-600 to-emerald-600 px-7 py-3 text-xs font-bold text-white hover:from-teal-700 hover:to-emerald-700 transition shadow-lg shadow-teal-600/20 btn-hover-lift"
                    >
                      Proceed to Contact & Verification →
                    </button>
                  </div>
                </form>
              )}

              {/* STEP 2: NODAL OFFICER & EMAIL OTP VERIFICATION */}
              {step === 2 && (
                <form onSubmit={handleCreateDraft} className="space-y-6">
                  <div className="rounded-2xl border border-slate-200/90 border-t-4 border-t-teal-600 bg-white/95 backdrop-blur-sm p-6 sm:p-8 space-y-6 shadow-[0_8px_30px_rgb(15,23,42,0.06)]">
                    <div className="flex items-center gap-3 pb-2 border-b border-slate-100">
                      <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-teal-50 border border-teal-200 text-teal-700">
                        <UserCheck className="w-5 h-5" />
                      </div>
                      <div>
                        <h3 className="text-base font-bold text-slate-900">
                          Designated Nodal Officer & Two-Factor Authentication
                        </h3>
                        <p className="text-[11px] text-slate-500">
                          Medical superintendent credentials and 2FA email ownership verification
                        </p>
                      </div>
                    </div>

                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                      <div>
                        <label className="block text-xs font-semibold text-slate-700">
                          Nodal Officer / Medical Superintendent Name *
                        </label>
                        <input
                          type="text"
                          value={nodalOfficerName}
                          onChange={(e) => setNodalOfficerName(e.target.value)}
                          placeholder="e.g. Dr. Harpreet Singh"
                          className="mt-1.5 w-full rounded-xl border border-slate-300 bg-slate-50/50 px-3.5 py-2.5 text-xs text-slate-900 outline-none focus:bg-white focus:border-teal-600 focus:ring-4 focus:ring-teal-500/10 transition shadow-2xs"
                          required
                        />
                      </div>
                      <div>
                        <label className="block text-xs font-semibold text-slate-700">
                          Official Designation *
                        </label>
                        <input
                          type="text"
                          value={officialDesignation}
                          onChange={(e) => setOfficialDesignation(e.target.value)}
                          placeholder="e.g. Chief Medical Superintendent"
                          className="mt-1.5 w-full rounded-xl border border-slate-300 bg-slate-50/50 px-3.5 py-2.5 text-xs text-slate-900 outline-none focus:bg-white focus:border-teal-600 focus:ring-4 focus:ring-teal-500/10 transition shadow-2xs"
                          required
                        />
                      </div>
                    </div>

                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                      <div>
                        <label className="block text-xs font-semibold text-slate-700">
                          Official Contact Email *
                        </label>
                        <div className="mt-1.5 flex gap-2">
                          <input
                            type="email"
                            value={applicantEmail}
                            onChange={(e) => {
                              setApplicantEmail(e.target.value);
                              setEmailVerified(false);
                            }}
                            placeholder="e.g. nodal.hospital@punjab.gov.in"
                            className="flex-1 rounded-xl border border-slate-300 bg-slate-50/50 px-3.5 py-2.5 text-xs text-slate-900 outline-none focus:bg-white focus:border-teal-600 focus:ring-4 focus:ring-teal-500/10 transition shadow-2xs"
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
                            className={`rounded-xl px-4 py-2.5 text-xs font-bold transition shadow-xs ${
                              emailVerified
                                ? "bg-emerald-50 text-emerald-800 border border-emerald-300"
                                : "bg-teal-700 text-white hover:bg-teal-800"
                            }`}
                          >
                            {emailVerified ? "✓ Verified" : "Verify Email"}
                          </button>
                        </div>
                        {emailVerified && (
                          <p className="mt-1.5 text-[11px] text-emerald-700 font-semibold flex items-center gap-1">
                            <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600" />
                            <span>Two-Factor Email Ownership Confirmed</span>
                          </p>
                        )}
                      </div>

                      <div>
                        <label className="block text-xs font-semibold text-slate-700">
                          Official Phone Number *
                        </label>
                        <input
                          type="tel"
                          value={applicantPhone}
                          onChange={(e) => setApplicantPhone(e.target.value)}
                          placeholder="e.g. +91 98765 43210"
                          className="mt-1.5 w-full rounded-xl border border-slate-300 bg-slate-50/50 px-3.5 py-2.5 text-xs text-slate-900 outline-none focus:bg-white focus:border-teal-600 focus:ring-4 focus:ring-teal-500/10 transition shadow-2xs"
                          required
                        />
                      </div>
                    </div>
                  </div>

                  <div className="flex justify-between items-center pt-2">
                    <button
                      type="button"
                      onClick={() => setStep(1)}
                      className="rounded-xl border border-slate-300 bg-white px-5 py-2.5 text-xs font-bold text-slate-700 hover:bg-slate-50 transition shadow-2xs"
                    >
                      ← Back to Facility
                    </button>

                    <button
                      type="submit"
                      disabled={loading || !emailVerified}
                      className="rounded-xl bg-gradient-to-r from-teal-600 to-emerald-600 px-7 py-3 text-xs font-bold text-white hover:from-teal-700 hover:to-emerald-700 disabled:opacity-50 transition shadow-lg shadow-teal-600/20 btn-hover-lift"
                    >
                      {loading ? "Creating Draft..." : "Save Draft & Proceed to Documents →"}
                    </button>
                  </div>
                </form>
              )}

              {/* STEP 3: MANDATORY DOCUMENT UPLOADS */}
              {step === 3 && (
                <div className="space-y-6">
                  <div className="rounded-2xl border border-slate-200/90 border-t-4 border-t-teal-600 bg-white/95 backdrop-blur-sm p-6 sm:p-8 space-y-6 shadow-[0_8px_30px_rgb(15,23,42,0.06)]">
                    <div className="flex items-center gap-3 pb-2 border-b border-slate-100">
                      <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-teal-50 border border-teal-200 text-teal-700">
                        <FileText className="w-5 h-5" />
                      </div>
                      <div>
                        <h3 className="text-base font-bold text-slate-900">
                          Upload Regulatory & Safety Documents
                        </h3>
                        <p className="text-[11px] text-slate-500">
                          Mandatory certificates undergo antivirus screening and cryptographic verification
                        </p>
                      </div>
                    </div>

                    <DocumentUploader
                      slots={HOSPITAL_DOC_SLOTS}
                      existingDocuments={application?.documents || []}
                      applicantToken={applicantToken}
                      canEdit={true}
                      onDocumentsChanged={refreshApplicationDocuments}
                    />
                  </div>

                  <div className="flex justify-between items-center pt-2">
                    <button
                      type="button"
                      onClick={() => setStep(2)}
                      className="rounded-xl border border-slate-300 bg-white px-5 py-2.5 text-xs font-bold text-slate-700 hover:bg-slate-50 transition shadow-2xs"
                    >
                      ← Back to Contact
                    </button>

                    <button
                      type="button"
                      onClick={handleProceedToStep4}
                      className="rounded-xl bg-gradient-to-r from-teal-600 to-emerald-600 px-7 py-3 text-xs font-bold text-white hover:from-teal-700 hover:to-emerald-700 transition shadow-lg shadow-teal-600/20 btn-hover-lift"
                    >
                      Review Application Summary →
                    </button>
                  </div>
                </div>
              )}

              {/* STEP 4: PREVIEW & FINAL SUBMISSION */}
              {step === 4 && (
                <div className="space-y-6">
                  <div className="rounded-2xl border border-slate-200/90 border-t-4 border-t-teal-600 bg-white/95 backdrop-blur-sm p-6 sm:p-8 space-y-6 shadow-[0_8px_30px_rgb(15,23,42,0.06)]">
                    <div className="border-b border-slate-100 pb-4">
                      <span className="rounded-full bg-teal-50 border border-teal-200 px-3 py-0.5 text-[10px] font-bold text-teal-800 uppercase tracking-wider">
                        Final Application Review
                      </span>
                      <h3 className="mt-2 text-xl font-extrabold text-slate-900">{facilityName}</h3>
                      <p className="text-xs text-slate-500">
                        Territorial Jurisdiction: {district}, {state}
                      </p>
                    </div>

                    {/* Summary Grid */}
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 text-xs">
                      <div className="rounded-xl border border-slate-200 bg-slate-50/70 p-4 space-y-2">
                        <h4 className="font-bold text-slate-900 uppercase tracking-wider text-[11px] pb-1 border-b border-slate-200">
                          Operational Capacities
                        </h4>
                        <p className="text-slate-600">Total Inpatient Beds: <strong className="text-slate-900">{totalBeds}</strong></p>
                        <p className="text-slate-600">ICU Beds: <strong className="text-slate-900">{icuBeds}</strong></p>
                        <p className="text-slate-600">Emergency Beds: <strong className="text-slate-900">{emergencyBeds}</strong></p>
                        <p className="text-slate-600">Ventilators: <strong className="text-slate-900">{ventilatorCount}</strong></p>
                        <p className="text-slate-600">24x7 Emergency Unit: <strong className="text-slate-900">{emergency24x7 ? "Yes" : "No"}</strong></p>
                      </div>

                      <div className="rounded-xl border border-slate-200 bg-slate-50/70 p-4 space-y-2">
                        <h4 className="font-bold text-slate-900 uppercase tracking-wider text-[11px] pb-1 border-b border-slate-200">
                          Nodal Authority Contact
                        </h4>
                        <p className="text-slate-600">Nodal Officer: <strong className="text-slate-900">{nodalOfficerName}</strong></p>
                        <p className="text-slate-600">Designation: <strong className="text-slate-900">{officialDesignation}</strong></p>
                        <p className="text-slate-600">Official Email: <strong className="text-slate-900">{applicantEmail}</strong></p>
                        <p className="text-slate-600">Phone: <strong className="text-slate-900">{applicantPhone}</strong></p>
                      </div>
                    </div>

                    {/* Documents Verified */}
                    <div>
                      <h4 className="font-bold text-slate-900 uppercase tracking-wider text-[11px] mb-2.5">
                        Uploaded Compliance Documents ({application?.documents.length || 0})
                      </h4>
                      <div className="space-y-2">
                        {application?.documents.map((d) => (
                          <div
                            key={d.document_id}
                            className="flex items-center justify-between rounded-xl border border-slate-200 bg-slate-50/50 p-3 text-xs"
                          >
                            <span className="font-medium text-slate-800">
                              {d.document_type}: {d.original_filename}
                            </span>
                            <span className="rounded-full bg-emerald-50 border border-emerald-300 px-2.5 py-0.5 text-[10px] text-emerald-800 font-bold">
                              ✓ Attached
                            </span>
                          </div>
                        ))}
                      </div>
                    </div>

                    {/* Legal Declaration */}
                    <div className="rounded-xl border border-teal-200 bg-teal-50/70 p-4 text-xs text-teal-900 space-y-1.5">
                      <p className="font-bold">Applicant Solemn Declaration:</p>
                      <p className="text-[11px] text-teal-800/90 leading-relaxed">
                        I solemnly affirm that the bed capacities, clinical certifications, and nodal authority contact details provided are genuine, authentic, and authorized under state Clinical Establishment guidelines.
                      </p>
                    </div>
                  </div>

                  <div className="flex justify-between items-center pt-2">
                    <button
                      type="button"
                      onClick={() => setStep(3)}
                      className="rounded-xl border border-slate-300 bg-white px-5 py-2.5 text-xs font-bold text-slate-700 hover:bg-slate-50 transition shadow-2xs"
                    >
                      ← Back to Documents
                    </button>

                    <button
                      type="button"
                      disabled={loading}
                      onClick={handleFinalSubmit}
                      className="rounded-xl bg-gradient-to-r from-emerald-600 to-teal-600 px-8 py-3.5 text-xs font-bold text-white hover:from-emerald-700 hover:to-teal-700 disabled:opacity-50 transition shadow-lg shadow-emerald-600/20 btn-hover-lift"
                    >
                      {loading ? "Submitting Application..." : "Final Submit Application ✓"}
                    </button>
                  </div>
                </div>
              )}
            </div>

            {/* Sticky Accreditation Checklist Sidebar */}
            <div className="hidden lg:block lg:col-span-4 lg:sticky lg:top-24 space-y-6">
              {/* Card 1: Accreditation Checklist */}
              <div className="rounded-2xl border border-slate-200/90 bg-white/95 backdrop-blur-sm p-6 space-y-4 shadow-[0_8px_30px_rgb(15,23,42,0.04)] card-hover-lift">
                <div className="flex items-center gap-2.5 pb-2 border-b border-slate-100">
                  <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-teal-50 text-teal-700 border border-teal-200">
                    <FileCheck2 className="w-4 h-4" />
                  </div>
                  <h4 className="text-xs font-bold uppercase tracking-wider text-slate-900">
                    Accreditation Checklist
                  </h4>
                </div>
                <ul className="space-y-3 text-xs text-slate-600">
                  <li className="flex items-start gap-2.5">
                    <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0 mt-0.5" />
                    <span>Clinical Establishment Act Certificate</span>
                  </li>
                  <li className="flex items-start gap-2.5">
                    <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0 mt-0.5" />
                    <span>Fire Department Safety NOC</span>
                  </li>
                  <li className="flex items-start gap-2.5">
                    <CheckCircle2 className="w-4 h-4 text-teal-600 shrink-0 mt-0.5" />
                    <span>Bio-Medical Waste Management NOC</span>
                  </li>
                  <li className="flex items-start gap-2.5">
                    <CheckCircle2 className="w-4 h-4 text-slate-400 shrink-0 mt-0.5" />
                    <span>NABH / NMC Teaching Accreditation</span>
                  </li>
                </ul>
              </div>

              {/* Card 2: 3-Tier Verification Hierarchy */}
              <div className="rounded-2xl border border-slate-200/90 bg-white/95 backdrop-blur-sm p-6 space-y-4 shadow-[0_8px_30px_rgb(15,23,42,0.04)] card-hover-lift">
                <div className="flex items-center gap-2.5 pb-2 border-b border-slate-100">
                  <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-indigo-50 text-indigo-700 border border-indigo-200">
                    <Clock className="w-4 h-4" />
                  </div>
                  <h4 className="text-xs font-bold uppercase tracking-wider text-slate-900">
                    Review Hierarchy
                  </h4>
                </div>
                <div className="space-y-3 text-xs">
                  <div className="p-3 rounded-xl bg-slate-50 border border-slate-200 space-y-1">
                    <span className="font-bold text-teal-800">Stage 1 • District CMO Review</span>
                    <p className="text-slate-500 text-[11px]">
                      Verification of physical bed inventory and facility registration.
                    </p>
                  </div>
                  <div className="p-3 rounded-xl bg-slate-50 border border-slate-200 space-y-1">
                    <span className="font-bold text-indigo-800">Stage 2 • State Directorate</span>
                    <p className="text-slate-500 text-[11px]">
                      Secondary compliance check & inter-district network mapping.
                    </p>
                  </div>
                  <div className="p-3 rounded-xl bg-slate-50 border border-slate-200 space-y-1">
                    <span className="font-bold text-purple-800">Stage 3 • Central Sign-Off</span>
                    <p className="text-slate-500 text-[11px]">
                      Apex accreditation approval and secure password activation token dispatch.
                    </p>
                  </div>
                </div>
              </div>

              {/* Card 3: Support Desk Contact */}
              <div className="rounded-2xl border border-slate-200/90 bg-[#0B132B] text-white p-6 space-y-3.5 shadow-md">
                <div className="flex items-center gap-2">
                  <HelpCircle className="w-4 h-4 text-teal-400" />
                  <span className="text-xs font-bold uppercase tracking-wider text-teal-300">
                    Onboarding Helpdesk
                  </span>
                </div>
                <p className="text-[11px] text-slate-300 leading-relaxed">
                  Need assistance with accreditation documentation or OTP verification? Write to our technical desk:
                </p>
                <div className="space-y-1.5 text-xs">
                  <div className="flex items-center gap-2 text-slate-200">
                    <Mail className="w-3.5 h-3.5 text-teal-400 shrink-0" />
                    <a
                      href="mailto:pawanbussiness108@gmail.com"
                      className="text-teal-300 hover:text-white underline font-mono text-[11px]"
                    >
                      pawanbussiness108@gmail.com
                    </a>
                  </div>
                  <div className="flex items-center gap-2 text-slate-300 text-[11px]">
                    <Phone className="w-3.5 h-3.5 text-emerald-400 shrink-0" />
                    <span>Helpline: <strong>108</strong> (Ambulance) • <strong>1075</strong> (Health)</span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* OTP Verification Modal */}
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
