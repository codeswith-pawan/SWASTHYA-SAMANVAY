"use client";

import React, { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import {
  Eye,
  EyeOff,
  ArrowLeft,
  AlertTriangle,
  Shield,
  ArrowRight,
  ChevronRight,
} from "lucide-react";
import { GovernmentHeader } from "@/components/shared/GovernmentHeader";
import { GovernmentFooter } from "@/components/shared/GovernmentFooter";
import { apiLogin, setStoredSession, clearStoredSession } from "@/lib/api";
import { Role } from "@/lib/types";

export interface DepartmentLoginPageProps {
  department: "hospital" | "district" | "state" | "central";
  title: string;
  subtitle: string;
  tier: string;
  expectedRole: Role;
  icon: React.ComponentType<{ className?: string }>;
  accentColor: {
    bg: string;
    text: string;
    border: string;
    button: string;
    lightBg: string;
  };
}

const ROLE_TO_PORTAL_MAP: Record<string, { name: string; path: string }> = {
  HOSPITAL: { name: "Hospital Portal", path: "/portal/hospital/login" },
  DISTRICT_ADMIN: { name: "District Portal", path: "/portal/district/login" },
  STATE_ADMIN: { name: "State Portal", path: "/portal/state/login" },
  CENTRAL_ADMIN: { name: "Central Portal", path: "/portal/central/login" },
};

export const DepartmentLoginPage: React.FC<DepartmentLoginPageProps> = ({
  department,
  title,
  subtitle,
  tier,
  expectedRole,
  icon: DeptIcon,
  accentColor,
}) => {
  const router = useRouter();

  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [roleMismatch, setRoleMismatch] = useState<{
    detectedRole: string;
    authorizedPortal: { name: string; path: string };
  } | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!username.trim() || !password.trim()) {
      setError("Please provide both username and password.");
      return;
    }

    setLoading(true);
    setError("");
    setRoleMismatch(null);

    try {
      const result = await apiLogin(username.trim(), password);

      // Strict Role-Based Verification: Validate that user role matches this department portal
      if (result.user.role !== expectedRole) {
        // Clear any stored credentials to prevent unauthorized cross-tier access
        clearStoredSession();

        const properPortal = ROLE_TO_PORTAL_MAP[result.user.role] || {
          name: "Authorized Portal",
          path: "/portal",
        };

        setRoleMismatch({
          detectedRole: result.user.role,
          authorizedPortal: properPortal,
        });
        return;
      }

      // Valid credentials and role matches department
      setStoredSession(result.user, result.access_token);
      window.location.href = "/";
    } catch (err: unknown) {
      const errorMsg =
        err instanceof Error
          ? err.message
          : "Invalid authentication credentials. Please try again.";
      setError(errorMsg);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-[#F4F8FC] flex flex-col font-sans text-[#14243B]">
      <GovernmentHeader />

      {/* Breadcrumb Section */}
      <div className="bg-white border-b border-[#DCE5EF] py-3 px-4 sm:px-6">
        <div className="max-w-7xl mx-auto flex items-center justify-between text-xs">
          <div className="flex items-center gap-2 text-[#60738C]">
            <Link href="/" className="hover:text-[#0B2345] font-medium transition">
              Home
            </Link>
            <ChevronRight className="w-3.5 h-3.5 text-[#60738C]/60" />
            <Link href="/portal" className="hover:text-[#0B2345] font-medium transition">
              Department Selection
            </Link>
            <ChevronRight className="w-3.5 h-3.5 text-[#60738C]/60" />
            <span className="text-[#14243B] font-semibold">{title}</span>
          </div>

          <Link
            href="/portal"
            className="inline-flex items-center gap-1.5 text-[#008F83] font-semibold hover:underline"
          >
            <ArrowLeft className="w-3.5 h-3.5" />
            <span>Switch Department</span>
          </Link>
        </div>
      </div>

      {/* Main Login View */}
      <main className="flex-1 flex items-center justify-center py-12 px-4 sm:px-6">
        <div className="w-full max-w-md space-y-6">
          {/* Back Navigation Button */}
          <Link
            href="/portal"
            className="inline-flex items-center gap-2 text-xs font-semibold text-[#60738C] hover:text-[#0B2345] transition"
          >
            <ArrowLeft className="w-4 h-4" />
            <span>Back to Department Selection</span>
          </Link>

          {/* Login Card */}
          <div className="rounded-2xl bg-white border border-[#DCE5EF] shadow-sm p-6 sm:p-8 space-y-6">
            {/* Header / Identity */}
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <div
                  className={`flex h-12 w-12 items-center justify-center rounded-xl border ${accentColor.lightBg} ${accentColor.border}`}
                >
                  <DeptIcon className={`w-6 h-6 ${accentColor.text}`} />
                </div>
                <span
                  className={`rounded-full px-2.5 py-0.5 text-[10px] font-bold tracking-wider uppercase border ${accentColor.lightBg} ${accentColor.text} ${accentColor.border}`}
                >
                  {tier}
                </span>
              </div>

              <div>
                <h1 className="text-xl sm:text-2xl font-extrabold text-[#14243B] tracking-tight">
                  {title}
                </h1>
                <p className="text-xs text-[#60738C] mt-1 leading-relaxed">
                  {subtitle}
                </p>
              </div>
            </div>

            {/* Role Mismatch Warning Banner */}
            {roleMismatch && (
              <div className="rounded-xl border border-[#D99A27]/40 bg-[#D99A27]/10 p-4 text-xs text-[#14243B] space-y-2.5">
                <div className="flex items-start gap-2.5">
                  <AlertTriangle className="w-4 h-4 text-[#D99A27] shrink-0 mt-0.5" />
                  <div>
                    <h2 className="text-xs font-bold text-[#D99A27] uppercase">
                      Department Role Mismatch
                    </h2>
                    <p className="mt-1 text-[#14243B]">
                      Your authenticated account has role <strong>{roleMismatch.detectedRole}</strong>, but this portal is reserved strictly for <strong>{expectedRole}</strong> personnel.
                    </p>
                  </div>
                </div>

                <div className="pt-2 border-t border-[#D99A27]/20 flex justify-end">
                  <Link
                    href={roleMismatch.authorizedPortal.path}
                    className="inline-flex items-center gap-1.5 rounded-lg bg-[#D99A27] text-white px-3 py-1.5 text-xs font-bold hover:bg-[#b57e1b] transition shadow-xs"
                  >
                    <span>Proceed to {roleMismatch.authorizedPortal.name}</span>
                    <ArrowRight className="w-3.5 h-3.5" />
                  </Link>
                </div>
              </div>
            )}

            {/* Standard Login Error Banner */}
            {error && !roleMismatch && (
              <div className="rounded-xl border border-[#D94B4B]/30 bg-[#D94B4B]/10 p-3.5 text-xs text-[#D94B4B] flex items-start gap-2.5">
                <AlertTriangle className="w-4 h-4 text-[#D94B4B] shrink-0 mt-0.5" />
                <span className="font-medium">{error}</span>
              </div>
            )}

            {/* Authentication Form */}
            <form onSubmit={handleSubmit} className="space-y-4">
              <div>
                <label className="block text-xs font-bold text-[#14243B] uppercase tracking-wider">
                  Official Username / Handle
                </label>
                <div className="mt-1.5 relative">
                  <input
                    type="text"
                    value={username}
                    onChange={(e) => setUsername(e.target.value)}
                    placeholder={
                      department === "hospital"
                        ? "e.g. gh00046 or facility handle"
                        : department === "district"
                        ? "e.g. amritsar_district_admin"
                        : department === "state"
                        ? "e.g. punjab_admin"
                        : "e.g. central_admin"
                    }
                    required
                    className="w-full rounded-lg border border-[#DCE5EF] bg-white px-3.5 py-2.5 text-xs text-[#14243B] placeholder-[#60738C]/50 focus:outline-none focus:border-[#008F83] focus:ring-4 focus:ring-[#008F83]/10 transition"
                  />
                </div>
              </div>

              <div>
                <div className="flex items-center justify-between">
                  <label className="block text-xs font-bold text-[#14243B] uppercase tracking-wider">
                    Password
                  </label>
                  <Link
                    href="/forgot-password"
                    className="text-xs font-semibold text-[#008F83] hover:text-[#0B2345] transition"
                  >
                    Forgot Password?
                  </Link>
                </div>

                <div className="mt-1.5 relative">
                  <input
                    type={showPassword ? "text" : "password"}
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    placeholder="Enter official password"
                    required
                    className="w-full rounded-lg border border-[#DCE5EF] bg-white px-3.5 py-2.5 pr-10 text-xs text-[#14243B] placeholder-[#60738C]/50 focus:outline-none focus:border-[#008F83] focus:ring-4 focus:ring-[#008F83]/10 transition"
                  />
                  <button
                    type="button"
                    onClick={() => setShowPassword(!showPassword)}
                    className="absolute right-3 top-1/2 -translate-y-1/2 text-[#60738C] hover:text-[#14243B]"
                    aria-label={showPassword ? "Hide password" : "Show password"}
                  >
                    {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                  </button>
                </div>
              </div>

              <button
                type="submit"
                disabled={loading}
                className={`w-full rounded-lg py-2.5 px-4 text-xs font-bold text-white transition shadow-xs flex items-center justify-center gap-2 ${accentColor.button} disabled:opacity-50`}
              >
                {loading && (
                  <span className="h-3.5 w-3.5 animate-spin rounded-full border-2 border-white border-t-transparent" />
                )}
                <span>
                  {loading
                    ? "Authenticating Authority..."
                    : `Sign In to ${department.charAt(0).toUpperCase() + department.slice(1)} Portal`}
                </span>
              </button>
            </form>

            {/* Quick Registration & Help Links */}
            <div className="pt-4 border-t border-[#DCE5EF]/60 flex flex-col gap-2 text-xs text-[#60738C]">
              <div className="flex items-center justify-between">
                <span>Unregistered facility or authority?</span>
                <Link href="/register" className="font-semibold text-[#008F83] hover:text-[#0B2345] transition">
                  Register Facility →
                </Link>
              </div>
              <div className="flex items-center justify-between">
                <span>Approved applicant?</span>
                <Link href="/activate" className="font-semibold text-[#0A9878] hover:text-[#07182F] transition">
                  Activate Account →
                </Link>
              </div>
              <div className="flex items-center justify-between">
                <span>Check submitted application?</span>
                <Link href="/application/track" className="font-semibold text-[#60738C] hover:text-[#14243B] transition">
                  Track Application →
                </Link>
              </div>
            </div>
          </div>

          {/* Security Assurance Notice */}
          <div className="rounded-xl border border-[#DCE5EF] bg-white p-4 text-[11px] text-[#60738C] flex items-start gap-2.5 shadow-2xs">
            <Shield className="w-4 h-4 text-[#008F83] shrink-0 mt-0.5" />
            <p>
              This is a restricted healthcare access gateway. All authentication attempts and system actions are logged and audited in accordance with role-based access control policies.
            </p>
          </div>
        </div>
      </main>

      <GovernmentFooter />
    </div>
  );
};