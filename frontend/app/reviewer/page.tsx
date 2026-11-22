"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { User } from "@/lib/types";
import { getStoredUser } from "@/lib/api";
import { RegistrationNavbar } from "@/components/registration/RegistrationNavbar";
import { ReviewerPortal } from "@/components/reviewer/ReviewerPortal";
import { ShieldCheck, Lock, ArrowRight, UserCheck, ChevronRight } from "lucide-react";

export default function ReviewerPage() {
  const [user, setUser] = useState<User | null>(null);
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
    const stored = getStoredUser();
    if (stored) {
      setUser(stored);
    }
  }, []);

  if (!mounted) {
    return (
      <div className="min-h-screen bg-[#F4F8FC] text-[#14243B] flex items-center justify-center">
        <div className="text-xs text-[#60738C] flex items-center gap-2">
          <div className="w-4 h-4 rounded-full border-2 border-[#008F83] border-t-transparent animate-spin" />
          Loading reviewer authentication session...
        </div>
      </div>
    );
  }

  const isReviewer =
    user && (user.role === "DISTRICT_ADMIN" || user.role === "STATE_ADMIN" || user.role === "CENTRAL_ADMIN");

  if (!isReviewer) {
    return (
      <div className="min-h-screen bg-[#F4F8FC] text-[#14243B] flex flex-col font-sans">
        <RegistrationNavbar />
        <main className="flex-1 flex items-center justify-center p-6">
          <div className="max-w-md w-full gov-card p-8 text-center space-y-5 bg-white border border-[#DCE5EF] shadow-lg animate-fade-in-up">
            <div className="mx-auto flex h-14 w-14 items-center justify-center rounded-2xl bg-teal-50 border border-teal-200 text-[#008F83] shadow-xs">
              <Lock className="w-7 h-7" />
            </div>
            <div>
              <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-teal-50 border border-teal-200 text-[#008F83] text-xs font-bold mb-2">
                <ShieldCheck className="w-3.5 h-3.5" />
                Authorized Review Personnel Only
              </span>
              <h1 className="text-xl font-bold text-[#0B2345]">Reviewer Session Required</h1>
              <p className="text-xs text-[#60738C] mt-2 leading-relaxed">
                Access to the Healthcare Registration Review Queue requires an authenticated District, State, or Central health administrator session.
              </p>
            </div>
            <div className="pt-2">
              <Link
                href="/portal"
                className="inline-flex items-center justify-center gap-2 w-full rounded-xl bg-gradient-to-r from-[#008F83] to-[#00A99D] px-5 py-3 text-xs font-bold text-white hover:from-[#007A70] hover:to-[#008F83] transition shadow-md shadow-[#008F83]/20"
              >
                <span>Sign In via Department Portals</span>
                <ArrowRight className="w-4 h-4" />
              </Link>
            </div>
          </div>
        </main>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[#F4F8FC] text-[#14243B] flex flex-col font-sans">
      <RegistrationNavbar />
      <main className="flex-1 mx-auto w-full max-w-7xl px-4 sm:px-6 lg:px-8 py-8 space-y-6">
        {/* Header Breadcrumb & Reviewer Identification Banner */}
        <div className="gov-card p-5 sm:p-6 bg-white border border-[#DCE5EF] flex flex-wrap items-center justify-between gap-4">
          <div>
            <div className="flex items-center gap-2 mb-1.5">
              <span className="rounded-full bg-teal-50 border border-teal-200 px-3 py-0.5 text-[10px] font-bold text-[#008F83] uppercase tracking-wider">
                Government Reviewer Command
              </span>
              <span className="text-xs font-semibold text-[#0B2345]">
                Jurisdiction Tier: <strong className="text-[#008F83]">{user.role.replace(/_/g, " ")}</strong>
              </span>
            </div>
            <h1 className="text-xl sm:text-2xl font-extrabold text-[#0B2345]">
              Healthcare Registration Review Queue
            </h1>
            <p className="text-xs text-[#60738C] mt-0.5">
              Reviewing Officer: <strong className="text-[#14243B]">{user.name}</strong> ({user.username}) {user.district ? `• District: ${user.district}` : ""} {user.state ? `• State: ${user.state}` : ""}
            </p>
          </div>

          <Link
            href="/"
            className="inline-flex items-center gap-1.5 rounded-xl border border-[#DCE5EF] bg-white px-4 py-2 text-xs font-bold text-[#0B2345] hover:bg-slate-50 transition shadow-xs"
          >
            <span>Open Clinical Dashboard</span>
            <ChevronRight className="w-3.5 h-3.5" />
          </Link>
        </div>

        <ReviewerPortal user={user} />
      </main>
    </div>
  );
}
