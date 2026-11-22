"use client";

import React, { useState, useEffect, Suspense } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import {
  Search,
  KeyRound,
  ShieldCheck,
  CheckCircle2,
  AlertCircle,
  ArrowRight,
  Clock,
  Building2,
  Lock,
} from "lucide-react";
import { RegistrationNavbar } from "@/components/registration/RegistrationNavbar";
import { ApplicationTimeline } from "@/components/registration/ApplicationTimeline";
import { apiPublicTrackApplication } from "@/lib/api";
import { PublicTrackingData } from "@/lib/types";

function TrackForm() {
  const searchParams = useSearchParams();
  const [appNumber, setAppNumber] = useState("");
  const [trackingToken, setTrackingToken] = useState("");
  const [trackingData, setTrackingData] = useState<PublicTrackingData | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const fetchTracking = async (app = appNumber, token = trackingToken) => {
    if (!app.trim() || !token.trim()) {
      setError("Please provide both Application Number and Secret Tracking Token.");
      return;
    }

    setLoading(true);
    setError("");
    setTrackingData(null);

    try {
      const data = await apiPublicTrackApplication(app.trim(), token.trim());
      setTrackingData(data);
    } catch (err: any) {
      setError(err.message || "Invalid application number or tracking token.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    const qApp = searchParams.get("app");
    const qToken = searchParams.get("token");
    if (qApp && qToken) {
      setAppNumber(qApp);
      setTrackingToken(qToken);
      fetchTracking(qApp, qToken);
    }
  }, [searchParams]);

  const handleTrack = (e: React.FormEvent) => {
    e.preventDefault();
    fetchTracking();
  };

  return (
    <div className="space-y-8">
      {/* Search Input Box */}
      <div className="rounded-2xl border border-slate-200/80 bg-white/95 backdrop-blur-sm p-6 sm:p-8 shadow-[0_8px_30px_rgb(15,23,42,0.06)]">
        <form onSubmit={handleTrack} className="space-y-4">
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">
                Official Application Number <span className="text-rose-500">*</span>
              </label>
              <div className="relative">
                <input
                  type="text"
                  value={appNumber}
                  onChange={(e) => setAppNumber(e.target.value)}
                  placeholder="e.g. APP-HOSP-202611-ABC123"
                  className="w-full rounded-xl border border-slate-300 bg-slate-50/50 px-3.5 py-2.5 text-xs sm:text-sm text-slate-900 placeholder-slate-400 focus:bg-white focus:border-teal-600 focus:ring-4 focus:ring-teal-500/10 font-mono outline-none transition-all"
                  required
                />
              </div>
            </div>
            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">
                Secret Tracking Token <span className="text-rose-500">*</span>
              </label>
              <div className="relative">
                <input
                  type="text"
                  value={trackingToken}
                  onChange={(e) => setTrackingToken(e.target.value)}
                  placeholder="16+ character secret token"
                  className="w-full rounded-xl border border-slate-300 bg-slate-50/50 px-3.5 py-2.5 text-xs sm:text-sm text-slate-900 placeholder-slate-400 focus:bg-white focus:border-teal-600 focus:ring-4 focus:ring-teal-500/10 font-mono outline-none transition-all"
                  required
                />
              </div>
            </div>
          </div>

          <div className="flex flex-wrap items-center justify-between gap-3 pt-2">
            <span className="text-[11px] text-slate-500 flex items-center gap-1.5">
              <Lock className="w-3.5 h-3.5 text-slate-400" />
              Confidential tracking token was generated upon registration submission.
            </span>
            <button
              type="submit"
              disabled={loading}
              className="inline-flex items-center gap-2 rounded-xl bg-gradient-to-r from-teal-600 to-emerald-600 px-6 py-2.5 text-xs sm:text-sm font-bold text-white hover:from-teal-700 hover:to-emerald-700 disabled:opacity-50 transition shadow-md shadow-teal-600/20"
            >
              <Search className="w-4 h-4" />
              {loading ? "Verifying..." : "Track Status"}
            </button>
          </div>
        </form>
      </div>

      {error && (
        <div className="rounded-2xl border border-rose-200 bg-rose-50/80 p-4 text-xs sm:text-sm text-rose-800 flex items-start gap-3 shadow-sm animate-fade-in-up">
          <AlertCircle className="w-5 h-5 text-rose-600 shrink-0 mt-0.5" />
          <div className="flex-1 font-medium leading-relaxed">{error}</div>
        </div>
      )}

      {/* Tracking Result View */}
      {trackingData && (
        <div className="space-y-6 animate-fade-in-up">
          <div className="rounded-2xl border border-slate-200/80 border-t-4 border-t-teal-600 bg-white/95 backdrop-blur-sm p-6 sm:p-7 space-y-4 shadow-[0_8px_30px_rgb(15,23,42,0.06)]">
            <div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-100 pb-4">
              <div>
                <span className="rounded-full bg-teal-50 px-2.5 py-0.5 text-[10px] font-bold text-teal-700 border border-teal-200 uppercase tracking-wider">
                  {trackingData.applicant_type} Facility
                </span>
                <h3 className="mt-1.5 text-lg font-bold text-slate-900">{trackingData.applicant_name}</h3>
                <p className="text-xs text-slate-500">
                  Jurisdiction: {trackingData.district ? `${trackingData.district}, ` : ""}{trackingData.state}
                </p>
              </div>

              <div className="text-right">
                <span className="text-[11px] text-slate-500 font-mono block">Reference</span>
                <span className="text-sm font-mono font-bold text-teal-700">
                  {trackingData.application_number}
                </span>
              </div>
            </div>

            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs">
              <div className="rounded-xl border border-slate-200 bg-slate-50/70 p-3">
                <span className="text-[10px] text-slate-500 uppercase font-semibold">Registered On</span>
                <p className="mt-1 text-slate-800 font-semibold font-mono">
                  {trackingData.created_at ? new Date(trackingData.created_at).toLocaleDateString() : "N/A"}
                </p>
              </div>

              <div className="rounded-xl border border-slate-200 bg-slate-50/70 p-3">
                <span className="text-[10px] text-slate-500 uppercase font-semibold">Submitted On</span>
                <p className="mt-1 text-slate-800 font-semibold font-mono">
                  {trackingData.submitted_at ? new Date(trackingData.submitted_at).toLocaleDateString() : "Draft"}
                </p>
              </div>

              <div className="rounded-xl border border-slate-200 bg-slate-50/70 p-3">
                <span className="text-[10px] text-slate-500 uppercase font-semibold">Review Level</span>
                <p className="mt-1 text-teal-700 font-bold">
                  {trackingData.current_stage.replace(/_/g, " ")}
                </p>
              </div>

              <div className="rounded-xl border border-slate-200 bg-slate-50/70 p-3">
                <span className="text-[10px] text-slate-500 uppercase font-semibold">Version</span>
                <p className="mt-1 text-slate-800 font-semibold font-mono">
                  v{trackingData.resubmission_version}
                </p>
              </div>
            </div>
          </div>

          {/* Timeline Component */}
          <ApplicationTimeline
            status={trackingData.status}
            currentStage={trackingData.current_stage}
            milestones={trackingData.milestones}
            resubmissionVersion={trackingData.resubmission_version}
          />

          {/* Callout to Authenticated Applicant View */}
          <div className="rounded-2xl border border-teal-200 bg-teal-50/60 p-5 flex flex-col sm:flex-row items-center justify-between gap-4 text-xs shadow-sm">
            <div>
              <p className="font-bold text-slate-900">Need to update documents or address reviewer feedback?</p>
              <p className="text-slate-600 mt-0.5">
                Sign in with an email verification code to view private documents and submit corrections.
              </p>
            </div>
            <Link
              href="/application/status"
              className="shrink-0 inline-flex items-center gap-1.5 rounded-xl bg-teal-700 px-4 py-2 font-bold text-white hover:bg-teal-800 transition shadow-sm"
            >
              Sign In to Applicant Portal <ArrowRight className="w-3.5 h-3.5" />
            </Link>
          </div>
        </div>
      )}
    </div>
  );
}

export default function ApplicationTrackPage() {
  return (
    <div className="min-h-screen bg-[#F4F8FC] text-[#14243B] flex flex-col font-sans">
      <RegistrationNavbar />

      <main className="flex-1 mx-auto w-full max-w-4xl px-4 sm:px-6 py-10 sm:py-14 space-y-8">
        <div className="text-center max-w-2xl mx-auto space-y-2">
          <nav className="flex items-center justify-center gap-2 text-xs font-medium text-slate-500 mb-2">
            <Link href="/" className="hover:text-teal-700 transition">Portal Home</Link>
            <span>/</span>
            <Link href="/register" className="hover:text-teal-700 transition">Registration Hub</Link>
            <span>/</span>
            <span className="text-slate-800 font-semibold">Track Application</span>
          </nav>
          <span className="inline-flex items-center gap-1.5 rounded-full bg-teal-50 px-3 py-1 text-xs font-bold text-teal-800 border border-teal-200 uppercase tracking-wider">
            <ShieldCheck className="w-3.5 h-3.5 text-teal-700" />
            Public Milestone Tracking
          </span>
          <h1 className="text-2xl sm:text-3xl font-extrabold text-slate-900 tracking-tight">
            Track Application Verification Status
          </h1>
          <p className="text-xs sm:text-sm text-slate-600">
            Enter your official registration reference number and confidential tracking token to check real-time approval milestones.
          </p>
        </div>

        <Suspense fallback={<div className="text-center text-slate-500 text-xs py-10">Loading tracking portal...</div>}>
          <TrackForm />
        </Suspense>
      </main>
    </div>
  );
}
