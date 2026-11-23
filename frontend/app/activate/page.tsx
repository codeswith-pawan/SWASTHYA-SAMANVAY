"use client";

import React, { useState, useEffect, Suspense } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import {
  Lock,
  KeyRound,
  ShieldCheck,
  CheckCircle2,
  AlertCircle,
  ArrowRight,
  UserCheck,
  Check,
} from "lucide-react";
import { RegistrationNavbar } from "@/components/registration/RegistrationNavbar";
import { apiActivateAccount } from "@/lib/api";
import { AccountActivationResponse } from "@/lib/types";

function ActivateForm() {
  const searchParams = useSearchParams();
  const [token, setToken] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [activationResult, setActivationResult] = useState<AccountActivationResponse | null>(null);

  useEffect(() => {
    const qToken = searchParams.get("token");
    if (qToken) {
      setToken(qToken);
    }
  }, [searchParams]);

  // Password Policy Checklist
  const hasMinLength = password.length >= 8;
  const hasUpper = /[A-Z]/.test(password);
  const hasLower = /[a-z]/.test(password);
  const hasDigit = /[0-9]/.test(password);
  const hasSpecial = /[!@#$%^&*()_+\-=\[\]{}|;:,.<>?]/.test(password);
  const passwordsMatch = password.length > 0 && password === confirmPassword;
  const isPasswordValid = hasMinLength && hasUpper && hasLower && hasDigit && hasSpecial && passwordsMatch;

  const handleActivate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!token.trim()) {
      setError("Please provide a valid single-use activation token.");
      return;
    }

    if (!isPasswordValid) {
      setError("Password does not meet all security policy requirements.");
      return;
    }

    setLoading(true);
    setError("");

    try {
      const res = await apiActivateAccount({
        activation_token: token.trim(),
        password,
        confirm_password: confirmPassword,
      });
      setActivationResult(res);
    } catch (err: any) {
      setError(
        err.message ||
          "Activation failed. The token may be invalid, expired (72h limit), or already consumed."
      );
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="w-full max-w-lg mx-auto">
      {/* SUCCESS CONFIRMATION VIEW */}
      {activationResult ? (
        <div className="rounded-3xl border border-emerald-200 bg-white/95 backdrop-blur-sm p-8 sm:p-10 text-center space-y-6 shadow-[0_8px_30px_rgb(15,23,42,0.08)]">
          <div className="mx-auto flex h-16 w-16 items-center justify-center rounded-2xl bg-emerald-100 border border-emerald-200 text-emerald-600 shadow-sm">
            <CheckCircle2 className="w-10 h-10" />
          </div>
          <div>
            <span className="rounded-full bg-emerald-50 px-3.5 py-1 text-xs font-bold text-emerald-700 border border-emerald-200 uppercase tracking-wider">
              Account Activated Successfully
            </span>
            <h2 className="mt-3 text-2xl font-bold text-slate-900">
              Welcome to SWASTHYA SAMANVAY Operations
            </h2>
            <p className="mt-2 text-xs sm:text-sm text-slate-600">
              Your credentials have been securely provisioned and stored with PBKDF2-HMAC-SHA256 encryption.
            </p>
          </div>

          <div className="rounded-2xl border border-slate-200 bg-slate-50 p-5 text-left space-y-2.5 font-mono text-xs">
            <div>
              <span className="text-[10px] text-slate-500 uppercase font-sans font-bold">Assigned Username</span>
              <p className="text-sm font-bold text-teal-700 select-all">{activationResult.username}</p>
            </div>
            <div className="border-t border-slate-200 pt-2 flex justify-between">
              <div>
                <span className="text-[10px] text-slate-500 uppercase font-sans font-bold">Assigned Role</span>
                <p className="text-slate-800 font-semibold">{activationResult.role}</p>
              </div>
              <div className="text-right">
                <span className="text-[10px] text-slate-500 uppercase font-sans font-bold">Application</span>
                <p className="text-slate-600">{activationResult.application_number}</p>
              </div>
            </div>
          </div>

          <div className="pt-2">
            <Link
              href="/portal/hospital/login"
              className="inline-flex items-center justify-center gap-2 w-full text-center rounded-xl bg-gradient-to-r from-teal-600 to-emerald-600 py-3 text-xs sm:text-sm font-bold text-white hover:from-teal-700 hover:to-emerald-700 transition shadow-md shadow-teal-600/20"
            >
              Sign In to Healthcare Dashboard <ArrowRight className="w-4 h-4" />
            </Link>
          </div>
        </div>
      ) : (
        /* ACTIVATION FORM */
        <div className="rounded-3xl border border-slate-200/80 border-t-4 border-t-teal-600 bg-white/95 backdrop-blur-sm p-6 sm:p-8 shadow-[0_8px_30px_rgb(15,23,42,0.08)] space-y-6">
          <div className="text-center space-y-2">
            <span className="inline-flex items-center gap-1.5 rounded-full bg-teal-50 px-3 py-1 text-xs font-bold text-teal-800 border border-teal-200 uppercase tracking-wider">
              <ShieldCheck className="w-3.5 h-3.5 text-teal-700" />
              Official Account Provisioning
            </span>
            <h1 className="text-2xl font-bold text-slate-900">
              Activate Operational Account
            </h1>
            <p className="text-xs sm:text-sm text-slate-600">
              Set your initial operational password to activate your approved healthcare portal account.
            </p>
          </div>

          {error && (
            <div className="rounded-2xl border border-rose-200 bg-rose-50/80 p-4 text-xs sm:text-sm text-rose-800 flex items-start gap-3 shadow-sm animate-fade-in-up">
              <AlertCircle className="w-5 h-5 text-rose-600 shrink-0 mt-0.5" />
              <div className="flex-1 font-medium leading-relaxed">{error}</div>
            </div>
          )}

          <form onSubmit={handleActivate} className="space-y-4">
            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">
                Single-Use Activation Token <span className="text-rose-500">*</span>
              </label>
              <input
                type="text"
                value={token}
                onChange={(e) => setToken(e.target.value)}
                placeholder="Enter 32+ character activation token"
                className="w-full rounded-xl border border-slate-300 bg-slate-50/50 px-3.5 py-2.5 text-xs sm:text-sm text-slate-900 placeholder-slate-400 focus:bg-white focus:border-teal-600 focus:ring-4 focus:ring-teal-500/10 font-mono outline-none transition-all"
                required
              />
              <span className="mt-1 block text-[11px] text-slate-500">
                Supplied in your official approval notification email. Valid for 72 hours.
              </span>
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">
                New Operational Password <span className="text-rose-500">*</span>
              </label>
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="Enter secure password"
                className="w-full rounded-xl border border-slate-300 bg-slate-50/50 px-3.5 py-2.5 text-xs sm:text-sm text-slate-900 placeholder-slate-400 focus:bg-white focus:border-teal-600 focus:ring-4 focus:ring-teal-500/10 outline-none transition-all"
                required
              />
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">
                Confirm Operational Password <span className="text-rose-500">*</span>
              </label>
              <input
                type="password"
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                placeholder="Re-enter password"
                className="w-full rounded-xl border border-slate-300 bg-slate-50/50 px-3.5 py-2.5 text-xs sm:text-sm text-slate-900 placeholder-slate-400 focus:bg-white focus:border-teal-600 focus:ring-4 focus:ring-teal-500/10 outline-none transition-all"
                required
              />
            </div>

            {/* Password Complexity Checklist */}
            <div className="rounded-xl border border-slate-200 bg-slate-50/80 p-3.5 space-y-1.5 text-[11px]">
              <span className="font-bold text-slate-700 block mb-1">Password Policy Requirements:</span>
              <div className="grid grid-cols-2 gap-1.5">
                <span className={hasMinLength ? "text-emerald-700 font-semibold" : "text-slate-400"}>
                  {hasMinLength ? "✓" : "○"} At least 8 characters
                </span>
                <span className={hasUpper ? "text-emerald-700 font-semibold" : "text-slate-400"}>
                  {hasUpper ? "✓" : "○"} 1+ Uppercase letter (A-Z)
                </span>
                <span className={hasLower ? "text-emerald-700 font-semibold" : "text-slate-400"}>
                  {hasLower ? "✓" : "○"} 1+ Lowercase letter (a-z)
                </span>
                <span className={hasDigit ? "text-emerald-700 font-semibold" : "text-slate-400"}>
                  {hasDigit ? "✓" : "○"} 1+ Numeric digit (0-9)
                </span>
                <span className={hasSpecial ? "text-emerald-700 font-semibold" : "text-slate-400"}>
                  {hasSpecial ? "✓" : "○"} 1+ Special character
                </span>
                <span className={passwordsMatch ? "text-emerald-700 font-semibold" : "text-slate-400"}>
                  {passwordsMatch ? "✓" : "○"} Passwords match
                </span>
              </div>
            </div>

            <button
              type="submit"
              disabled={loading || !isPasswordValid || !token.trim()}
              className="w-full inline-flex items-center justify-center gap-2 rounded-xl bg-gradient-to-r from-teal-600 to-emerald-600 py-3 text-xs sm:text-sm font-bold text-white hover:from-teal-700 hover:to-emerald-700 disabled:opacity-40 transition shadow-md shadow-teal-600/20"
            >
              {loading ? "Activating Operational Account..." : "Confirm & Activate Account"}
              <ArrowRight className="w-4 h-4" />
            </button>
          </form>

          <div className="border-t border-slate-100 pt-4 flex items-center justify-between text-xs text-slate-500">
            <Link href="/activate/resend" className="text-teal-700 font-semibold hover:underline">
              Need to resend activation link?
            </Link>
            <Link href="/" className="hover:text-slate-800 transition">
              Back to Home
            </Link>
          </div>
        </div>
      )}
    </div>
  );
}

export default function ActivatePage() {
  return (
    <div className="min-h-screen bg-[#F4F8FC] text-[#14243B] flex flex-col font-sans">
      <RegistrationNavbar />
      <main className="flex-1 flex items-center justify-center p-4 sm:p-6 py-12">
        <Suspense fallback={<div className="text-xs text-slate-500">Loading activation session...</div>}>
          <ActivateForm />
        </Suspense>
      </main>
    </div>
  );
}
