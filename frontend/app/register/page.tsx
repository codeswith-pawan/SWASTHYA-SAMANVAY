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
  ChevronRight,
  HelpCircle,
} from "lucide-react";
import { RegistrationNavbar } from "@/components/registration/RegistrationNavbar";

export default function RegisterHubPage() {
  const [trackNumber, setTrackNumber] = useState("");
  const [trackToken, setTrackToken] = useState("");

  const tiers = [
    {
      type: "HOSPITAL",
      title: "Hospital & Healthcare Facility",
      tagline: "Facility Operations & Emergency Bed Capacity",
      desc: "For government, municipal, charitable, and accredited private hospitals providing emergency, ICU, and inpatient critical care.",
      badge: "Tier III • Clinical Facility",
      topBorder: "border-t-[#008F83]",
      icon: Hospital,
      iconBg: "bg-teal-50 text-[#008F83] border-teal-200",
      buttonBg: "bg-gradient-to-r from-[#008F83] to-[#00A99D] hover:from-[#007A70] hover:to-[#008F83]",
      href: "/register/hospital",
      requirements: [
        "Clinical Establishment Registration (Act / Reg. No.)",
        "Fire Safety NOC Clearance Certificate",
        "Designated Medical Superintendent / Nodal Contact",
        "ICU, Oxygen & Operational Bed Breakdown",
      ],
      cta: "Register Hospital Facility",
      recommended: true,
    },
    {
      type: "DISTRICT",
      title: "District Health Administration",
      tagline: "Chief Medical Officer (CMO) Authority",
      desc: "For territorial health offices supervising sub-district hospitals, community health centers, and localized triage quotas.",
      badge: "Tier II • District Authority",
      topBorder: "border-t-[#0B2345]",
      icon: Building2,
      iconBg: "bg-blue-50 text-[#0B2345] border-blue-200",
      buttonBg: "bg-gradient-to-r from-[#0B2345] to-[#143A6D] hover:from-[#07182F] hover:to-[#0B2345]",
      href: "/register/district",
      requirements: [
        "Official Gazetted Order / Government Notification",
        "Chief Medical Officer / Civil Surgeon Designation",
        "Official Government Domain Email (@gov.in / @nic.in)",
        "Assigned District Territorial Jurisdiction",
      ],
      cta: "Register District Authority",
      recommended: false,
    },
    {
      type: "STATE",
      title: "State Health Directorate",
      tagline: "Directorate of Health Services (DHS)",
      desc: "For State Health Departments governing regional referral networks, interstate patient transfers, and centralized quotas.",
      badge: "Tier I • State Directorate",
      topBorder: "border-t-[#00A99D]",
      icon: ShieldCheck,
      iconBg: "bg-emerald-50 text-[#00A99D] border-emerald-200",
      buttonBg: "bg-gradient-to-r from-[#00A99D] to-[#008F83] hover:from-[#008F83] hover:to-[#007A70]",
      href: "/register/state",
      requirements: [
        "State Health Mission Executive Resolution",
        "Principal Secretary / Director Authorization",
        "Official State Health Secretariat Domain Credentials",
        "Statewide Regional Command Scope",
      ],
      cta: "Register State Directorate",
      recommended: false,
    },
  ];

  return (
    <div className="min-h-screen bg-[#F4F8FC] text-[#14243B] flex flex-col font-sans">
      <RegistrationNavbar />

      <main className="flex-1 mx-auto w-full max-w-7xl px-4 sm:px-6 lg:px-8 py-10 sm:py-14 space-y-12">
        {/* Header Hero Section */}
        <div className="text-center max-w-3xl mx-auto space-y-3 animate-fade-in-up">
          <div className="inline-flex items-center gap-2 rounded-full bg-teal-50 border border-teal-200 px-3.5 py-1 text-xs font-bold text-[#008F83] tracking-wide shadow-xs">
            <Shield className="w-3.5 h-3.5" />
            <span>Accredited Healthcare Onboarding Network</span>
          </div>
          <h1 className="text-3xl sm:text-4xl font-extrabold tracking-tight text-[#0B2345]">
            Healthcare Entity Registration
          </h1>
          <p className="text-sm sm:text-base text-[#60738C] leading-relaxed">
            Select your administrative jurisdiction or medical facility classification to initiate the official multi-tier verification and credential provisioning workflow on SWASTHYA SAMANVAY.
          </p>
        </div>

        {/* 3 Registration Tier Cards */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 sm:gap-8 items-stretch">
          {tiers.map((t) => {
            const Icon = t.icon;
            return (
              <div
                key={t.type}
                className={`gov-card relative flex flex-col justify-between p-6 sm:p-7 border-t-4 ${t.topBorder} ${
                  t.recommended ? "ring-2 ring-[#008F83]/30" : ""
                }`}
              >
                {t.recommended && (
                  <div className="absolute -top-3.5 right-6 bg-[#008F83] text-white text-[10px] font-bold px-3 py-1 rounded-full uppercase tracking-wider shadow-sm">
                    Most Common
                  </div>
                )}

                <div className="space-y-4">
                  {/* Top Badge & Icon */}
                  <div className="flex items-center justify-between">
                    <div className={`p-3 rounded-xl border ${t.iconBg} shadow-xs`}>
                      <Icon className="w-6 h-6" />
                    </div>
                    <span className="text-[11px] font-bold text-[#60738C] uppercase tracking-wider">
                      {t.badge}
                    </span>
                  </div>

                  {/* Title & Description */}
                  <div>
                    <h2 className="text-lg font-bold text-[#0B2345] leading-snug">
                      {t.title}
                    </h2>
                    <p className="text-xs font-medium text-[#008F83] mt-0.5">
                      {t.tagline}
                    </p>
                    <p className="text-xs text-[#60738C] mt-2 leading-relaxed">
                      {t.desc}
                    </p>
                  </div>

                  {/* Prerequisites Checklist */}
                  <div className="pt-3 border-t border-[#DCE5EF] space-y-2">
                    <span className="text-[11px] font-bold uppercase tracking-wider text-[#0B2345] block">
                      Mandatory Documentation:
                    </span>
                    <ul className="space-y-1.5 text-xs text-[#14243B]">
                      {t.requirements.map((req, idx) => (
                        <li key={idx} className="flex items-start gap-2">
                          <CheckCircle2 className="w-3.5 h-3.5 text-[#0A9878] shrink-0 mt-0.5" />
                          <span className="text-[11px] leading-tight text-[#60738C]">{req}</span>
                        </li>
                      ))}
                    </ul>
                  </div>
                </div>

                {/* Card CTA */}
                <div className="pt-6 mt-6 border-t border-[#DCE5EF]">
                  <Link
                    href={t.href}
                    className={`w-full inline-flex items-center justify-center gap-2 rounded-xl py-3 px-4 text-xs font-bold text-white shadow-md transition-all ${t.buttonBg}`}
                  >
                    <span>{t.cta}</span>
                    <ArrowRight className="w-4 h-4" />
                  </Link>
                </div>
              </div>
            );
          })}
        </div>

        {/* Live Application Tracking Quick Access Strip */}
        <div className="gov-card p-6 sm:p-8 bg-white border border-[#DCE5EF] shadow-sm">
          <div className="flex flex-col lg:flex-row items-center justify-between gap-6">
            <div className="space-y-1 text-center lg:text-left">
              <div className="inline-flex items-center gap-1.5 text-xs font-bold text-[#008F83] uppercase tracking-wider">
                <FileCheck2 className="w-4 h-4" />
                <span>Already Registered?</span>
              </div>
              <h3 className="text-lg font-bold text-[#0B2345]">
                Track Existing Application Status
              </h3>
              <p className="text-xs text-[#60738C] max-w-xl">
                Enter your official Application Number and Secret Tracking Token provided during submission to view live multi-tier review milestones.
              </p>
            </div>

            <div className="flex flex-col sm:flex-row items-center gap-3 w-full lg:w-auto">
              <Link
                href="/application/track"
                className="w-full sm:w-auto inline-flex items-center justify-center gap-2 rounded-xl bg-[#0B2345] text-white px-6 py-3 text-xs font-bold hover:bg-[#07182F] transition shadow-sm"
              >
                <Search className="w-4 h-4 text-teal-400" />
                <span>Track Application &rarr;</span>
              </Link>
              <Link
                href="/application/status"
                className="w-full sm:w-auto inline-flex items-center justify-center gap-2 rounded-xl border border-[#DCE5EF] bg-white text-[#0B2345] px-5 py-3 text-xs font-bold hover:bg-slate-50 transition shadow-xs"
              >
                <Lock className="w-4 h-4 text-[#008F83]" />
                <span>Sign in to Applicant Portal</span>
              </Link>
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}
