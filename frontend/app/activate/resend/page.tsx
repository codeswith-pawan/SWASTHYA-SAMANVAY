"use client";

import React, { useState } from "react";
import Link from "next/link";
import {
  Mail,
  ShieldCheck,
  CheckCircle2,
  AlertCircle,
  ArrowRight,
  Send,
} from "lucide-react";
import { RegistrationNavbar } from "@/components/registration/RegistrationNavbar";
import { apiResendActivation } from "@/lib/api";

export default function ResendActivationPage() {
  const [appNumber, setAppNumber] = useState("");
  const [email, setEmail] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [successMsg, setSuccessMsg] = useState("");

  const handleResend = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!appNumber.trim() || !email.trim()) {
      setError("Please provide both Application Number and registered official email.");
      return;
    }

    setLoading(true);
    setError("");
    setSuccessMsg("");

    try {
      const res = await apiResendActivation({
        application_number: appNumber.trim(),
        applicant_email: email.trim(),
      });
      setSuccessMsg(res.message || "A fresh activation link has been sent to your email.");
    } catch (err: any) {
      setError(err.message || "Unable to resend activation link. Verify application details.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-[#F4F8FC] text-[#14243B] flex flex-col font-sans">
      <RegistrationNavbar />
      <main className="flex-1 flex items-center justify-center p-4 sm:p-6 py-12">
        <div className="w-full max-w-md rounded-3xl border border-slate-200/80 border-t-4 border-t-teal-600 bg-white/95 backdrop-blur-sm p-6 sm:p-8 shadow-[0_8px_30px_rgb(15,23,42,0.08)] space-y-6">
          <div className="text-center space-y-2">
            <span className="inline-flex items-center gap-1.5 rounded-full bg-teal-50 px-3 py-1 text-xs font-bold text-teal-800 border border-teal-200 uppercase tracking-wider">
              <ShieldCheck className="w-3.5 h-3.5 text-teal-700" />
              Activation Recovery
            </span>
            <h1 className="text-2xl font-bold text-slate-900">
              Resend Account Activation Link
            </h1>
            <p className="text-xs sm:text-sm text-slate-600">
              Enter your official application reference number and applicant email to receive a fresh single-use activation invitation.
            </p>
          </div>

          {error && (
            <div className="rounded-2xl border border-rose-200 bg-rose-50/80 p-4 text-xs sm:text-sm text-rose-800 flex items-start gap-3 shadow-sm animate-fade-in-up">
              <AlertCircle className="w-5 h-5 text-rose-600 shrink-0 mt-0.5" />
              <div className="flex-1 font-medium leading-relaxed">{error}</div>
            </div>
          )}

          {successMsg && (
            <div className="rounded-2xl border border-emerald-200 bg-emerald-50/80 p-4 text-xs sm:text-sm text-emerald-800 flex items-start gap-3 shadow-sm animate-fade-in-up">
              <CheckCircle2 className="w-5 h-5 text-emerald-600 shrink-0 mt-0.5" />
              <div className="flex-1 font-medium leading-relaxed">{successMsg}</div>
            </div>
          )}

          <form onSubmit={handleResend} className="space-y-4">
            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">
                Application Reference Number <span className="text-rose-500">*</span>
              </label>
              <input
                type="text"
                value={appNumber}
                onChange={(e) => setAppNumber(e.target.value)}
                placeholder="e.g. APP-HOSP-202611-ABC123"
                className="w-full rounded-xl border border-slate-300 bg-slate-50/50 px-3.5 py-2.5 text-xs sm:text-sm text-slate-900 placeholder-slate-400 focus:bg-white focus:border-teal-600 focus:ring-4 focus:ring-teal-500/10 font-mono outline-none transition-all"
                required
              />
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">
                Designated Applicant Email Address <span className="text-rose-500">*</span>
              </label>
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="e.g. nodal.officer@punjab.gov.in"
                className="w-full rounded-xl border border-slate-300 bg-slate-50/50 px-3.5 py-2.5 text-xs sm:text-sm text-slate-900 placeholder-slate-400 focus:bg-white focus:border-teal-600 focus:ring-4 focus:ring-teal-500/10 outline-none transition-all"
                required
              />
            </div>

            <button
              type="submit"
              disabled={loading}
              className="w-full inline-flex items-center justify-center gap-2 rounded-xl bg-gradient-to-r from-teal-600 to-emerald-600 py-3 text-xs sm:text-sm font-bold text-white hover:from-teal-700 hover:to-emerald-700 disabled:opacity-50 transition shadow-md shadow-teal-600/20"
            >
              <Send className="w-4 h-4" />
              {loading ? "Dispatching Activation Link..." : "Send Fresh Activation Link"}
            </button>
          </form>

          <div className="border-t border-slate-100 pt-4 flex items-center justify-between text-xs text-slate-500">
            <Link href="/activate" className="text-teal-700 font-semibold hover:underline">
              Have an activation token?
            </Link>
            <Link href="/" className="hover:text-slate-800 transition">
              Back to Home
            </Link>
          </div>
        </div>
      </main>
    </div>
  );
}
