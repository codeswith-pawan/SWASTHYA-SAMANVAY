"use client";

import React, { useState, useEffect } from "react";
import { apiSendRegistrationOTP, apiVerifyRegistrationOTP } from "@/lib/api";
import { OTPVerifyResponse } from "@/lib/types";
import { Mail, X, Lock, CheckCircle2, AlertCircle } from "lucide-react";

interface OTPModalProps {
  isOpen: boolean;
  onClose: () => void;
  contactTarget: string;
  purpose?: "REGISTRATION_OTP" | "PORTAL_ACCESS_OTP";
  applicationNumber?: string;
  onVerified: (response: OTPVerifyResponse) => void;
}

export const OTPModal: React.FC<OTPModalProps> = ({
  isOpen,
  onClose,
  contactTarget,
  purpose = "REGISTRATION_OTP",
  applicationNumber,
  onVerified,
}) => {
  const [tokenId, setTokenId] = useState<string | null>(null);
  const [otp, setOtp] = useState("");
  const [countdown, setCountdown] = useState(60);
  const [sending, setSending] = useState(false);
  const [verifying, setVerifying] = useState(false);
  const [error, setError] = useState("");
  const [infoMessage, setInfoMessage] = useState("");

  const handleRequestOTP = async () => {
    setSending(true);
    setError("");
    setInfoMessage("");
    setOtp("");

    try {
      const res = await apiSendRegistrationOTP({
        contact_target: contactTarget.trim(),
        channel: "EMAIL",
        purpose,
        application_number: applicationNumber,
      });

      setTokenId(res.token_id);
      setCountdown(res.resend_available_in_seconds || 60);
      setInfoMessage(`Verification code dispatched to ${contactTarget}.`);
    } catch (err: any) {
      setError(err.message || "Failed to dispatch verification code. Please check email address.");
    } finally {
      setSending(false);
    }
  };

  useEffect(() => {
    if (isOpen && contactTarget) {
      handleRequestOTP();
    } else {
      setOtp("");
      setError("");
      setInfoMessage("");
    }
  }, [isOpen, contactTarget]);

  useEffect(() => {
    let timer: NodeJS.Timeout;
    if (countdown > 0) {
      timer = setTimeout(() => setCountdown(countdown - 1), 1000);
    }
    return () => clearTimeout(timer);
  }, [countdown]);

  const handleVerify = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!tokenId) {
      setError("No active verification token. Please click Resend OTP.");
      return;
    }

    if (otp.trim().length !== 6) {
      setError("Please enter the 6-digit numeric verification code.");
      return;
    }

    setVerifying(true);
    setError("");

    try {
      const res = await apiVerifyRegistrationOTP({
        token_id: tokenId,
        otp: otp.trim(),
        purpose,
        application_number: applicationNumber,
      });

      if (res.verified) {
        onVerified(res);
        onClose();
      } else {
        setError(res.message || "Verification code could not be validated.");
      }
    } catch (err: any) {
      setError(err.message || "Invalid or expired verification code.");
    } finally {
      setVerifying(false);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/60 backdrop-blur-xs p-4">
      <div className="w-full max-w-md rounded-2xl border border-slate-200/90 bg-white p-6 sm:p-7 shadow-[0_20px_50px_rgba(15,23,42,0.15)] animate-fade-in-up">
        <div className="flex items-center justify-between border-b border-slate-100 pb-4">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-teal-50 border border-teal-200 text-teal-700 shadow-2xs">
              <Mail className="w-5 h-5" />
            </div>
            <div>
              <h3 className="text-base font-bold text-slate-900">Official Email Verification</h3>
              <p className="text-[11px] text-slate-500">Nodal Officer Two-Factor Authentication</p>
            </div>
          </div>
          <button
            onClick={onClose}
            type="button"
            className="rounded-lg p-1.5 text-slate-400 hover:bg-slate-100 hover:text-slate-700 transition"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        <form onSubmit={handleVerify} className="mt-5 space-y-4">
          <p className="text-xs text-slate-600 leading-relaxed">
            A 6-digit security verification code has been dispatched to:
            <br />
            <strong className="text-teal-900 font-semibold">{contactTarget}</strong>
          </p>

          <div>
            <label className="block text-xs font-semibold text-slate-700">
              Enter 6-Digit Security Code
            </label>
            <input
              type="text"
              inputMode="numeric"
              pattern="[0-9]*"
              maxLength={6}
              value={otp}
              onChange={(e) => setOtp(e.target.value.replace(/\D/g, ""))}
              placeholder="••••••"
              className="mt-1.5 w-full rounded-xl border border-slate-300 bg-slate-50/50 px-4 py-3 text-center text-2xl font-mono tracking-widest text-slate-900 placeholder-slate-300 outline-none focus:bg-white focus:border-teal-600 focus:ring-4 focus:ring-teal-500/10 transition shadow-2xs"
              autoFocus
              required
            />
          </div>

          {error && (
            <div className="rounded-xl border border-rose-200 bg-rose-50 p-3 text-xs text-rose-800 flex items-start gap-2">
              <AlertCircle className="w-4 h-4 text-rose-600 shrink-0 mt-0.5" />
              <span>{error}</span>
            </div>
          )}

          {infoMessage && (
            <div className="rounded-xl border border-teal-200 bg-teal-50 p-2.5 text-xs text-teal-800 flex items-start gap-2">
              <CheckCircle2 className="w-4 h-4 text-teal-600 shrink-0 mt-0.5" />
              <span>{infoMessage}</span>
            </div>
          )}

          <div className="flex items-center justify-between pt-1 text-xs">
            <button
              type="button"
              disabled={countdown > 0 || sending}
              onClick={handleRequestOTP}
              className={`font-semibold transition ${
                countdown > 0 || sending
                  ? "text-slate-400 cursor-not-allowed"
                  : "text-teal-700 hover:text-teal-900 underline"
              }`}
            >
              {sending ? "Sending Code..." : countdown > 0 ? `Resend Code in ${countdown}s` : "Resend Verification Code"}
            </button>
            <span className="text-[11px] text-slate-400">Expires in 10m</span>
          </div>

          <div className="pt-2">
            <button
              type="submit"
              disabled={verifying || otp.length !== 6}
              className="w-full rounded-xl bg-gradient-to-r from-teal-600 to-emerald-600 hover:from-teal-700 hover:to-emerald-700 text-white py-3 text-xs font-bold transition shadow-md shadow-teal-600/20 disabled:opacity-50 btn-hover-lift"
            >
              {verifying ? "Validating Security Code..." : "Confirm & Verify Email ✓"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
