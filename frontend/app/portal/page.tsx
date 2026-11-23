"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import {
  Building2,
  MapPin,
  ShieldCheck,
  Globe,
  ArrowRight,
  Lock,
  ChevronRight,
  Shield,
  CheckCircle2,
  UserCheck,
} from "lucide-react";
import { GovernmentHeader } from "@/components/shared/GovernmentHeader";
import { GovernmentFooter } from "@/components/shared/GovernmentFooter";
import { getStoredUser } from "@/lib/api";
import { User } from "@/lib/types";
import { useLanguage } from "@/lib/i18n";

export default function PortalSelectionPage() {
  const [currentUser, setCurrentUser] = useState<User | null>(null);
  const { isHindi } = useLanguage();

  useEffect(() => {
    const u = getStoredUser();
    if (u) setCurrentUser(u);
  }, []);

  const departments = [
    {
      id: "hospital",
      title: isHindi ? "अस्पताल पोर्टल" : "HOSPITAL PORTAL",
      tagline: isHindi ? "सुविधा संचालन एवं बेड आवंटन" : "Facility Operations & Bed Allocation",
      tier: isHindi ? "सुविधा स्तर" : "Facility Tier",
      icon: Building2,
      iconColor: "text-[#008F83] bg-[#008F83]/10 border-[#008F83]/30",
      badgeColor: "bg-[#008F83]/10 text-[#008F83] border-[#008F83]/30",
      buttonColor: "bg-[#0B2345] hover:bg-[#07182F] text-white",
      description: isHindi
        ? "इनपेशेंट प्रवेश, आईसीयू बेड इन्वेंट्री, आपातकालीन ट्रायज एवं अंतर-अस्पताल मरीज स्थानांतरण हेतु सुविधा-स्तरीय प्रबंधन।"
        : "Facility-level management for inpatient admissions, ICU bed inventory, emergency triage, and inter-hospital patient transfers.",
      features: isHindi
        ? [
            "अस्पताल प्रशासन",
            "बेड एवं इन्वेंट्री प्रबंधन",
            "मरीज रेफरल प्रक्रिया",
            "संचालन डैशबोर्ड",
          ]
        : [
            "Hospital administration",
            "Bed and inventory management",
            "Patient referrals",
            "Operational dashboard",
          ],
      loginPath: "/portal/hospital/login",
      loginText: isHindi ? "अस्पताल लॉगिन" : "Login to Hospital",
    },
    {
      id: "district",
      title: isHindi ? "जिला पोर्टल" : "DISTRICT PORTAL",
      tagline: isHindi ? "क्षेत्राधिकार निगरानी एवं प्रत्यायन" : "Jurisdiction Monitoring & Accreditation",
      tier: isHindi ? "जिला स्तर" : "District Tier",
      icon: MapPin,
      iconColor: "text-[#0B2345] bg-[#0B2345]/10 border-[#0B2345]/30",
      badgeColor: "bg-[#0B2345]/10 text-[#0B2345] border-[#0B2345]/30",
      buttonColor: "bg-[#0B2345] hover:bg-[#07182F] text-white",
      description: isHindi
        ? "जिला स्वास्थ्य निगरानी, अस्पताल पंजीकरण सत्यापन, आवेदन समीक्षा एवं स्थानीय समन्वय।"
        : "District health surveillance, hospital registration verification, application review, and localized coordination.",
      features: isHindi
        ? [
            "जिला अस्पताल निगरानी",
            "अस्पताल सत्यापन",
            "आवेदन समीक्षा",
            "जिला-स्तरीय समन्वय",
          ]
        : [
            "District hospital monitoring",
            "Hospital verification",
            "Application review",
            "District-level coordination",
          ],
      loginPath: "/portal/district/login",
      loginText: isHindi ? "जिला लॉगिन" : "Login to District",
    },
    {
      id: "state",
      title: isHindi ? "राज्य पोर्टल" : "STATE PORTAL",
      tagline: isHindi ? "निदेशालय निरीक्षण एवं नीतिगत अनुमोदन" : "Directorate Oversight & Policy Approvals",
      tier: isHindi ? "राज्य स्तर" : "State Tier",
      icon: ShieldCheck,
      iconColor: "text-[#008F83] bg-[#008F83]/10 border-[#008F83]/30",
      badgeColor: "bg-[#008F83]/10 text-[#008F83] border-[#008F83]/30",
      buttonColor: "bg-[#008F83] hover:bg-[#007A70] text-white",
      description: isHindi
        ? "राज्य-व्यापी अस्पताल प्रशासन, अंतर-जिला निगरानी, चरण-2 आवेदन अनुमोदन एवं क्षेत्रीय प्रदर्शन विश्लेषण।"
        : "State-wide hospital administration, inter-district monitoring, stage-2 application approvals, and regional performance analytics.",
      features: isHindi
        ? [
            "राज्य अस्पताल प्रशासन",
            "जिला निगरानी",
            "राज्य-स्तरीय अनुमोदन",
            "प्रदर्शन अवलोकन",
          ]
        : [
            "State hospital administration",
            "District monitoring",
            "State-level approvals",
            "Performance overview",
          ],
      loginPath: "/portal/state/login",
      loginText: isHindi ? "राज्य लॉगिन" : "Login to State",
    },
    {
      id: "central",
      title: isHindi ? "केंद्रीय पोर्टल" : "CENTRAL PORTAL",
      tagline: isHindi ? "राष्ट्रीय समन्वय एवं शासन" : "National Coordination & Governance",
      tier: isHindi ? "राष्ट्रीय स्तर" : "National Tier",
      icon: Globe,
      iconColor: "text-[#07182F] bg-[#07182F]/10 border-[#07182F]/30",
      badgeColor: "bg-[#07182F]/10 text-[#07182F] border-[#07182F]/30",
      buttonColor: "bg-[#07182F] hover:bg-[#0B2345] text-white",
      description: isHindi
        ? "राष्ट्रीय स्तर पर स्वास्थ्य निगरानी, शीर्ष अस्पताल प्रत्यायन अनुमोदन, राष्ट्रव्यापी बेड उपलब्धता ट्रैकिंग एवं प्रणाली नियंत्रण।"
        : "National-level surveillance, apex hospital accreditation approvals, nationwide bed availability tracking, and system oversight.",
      features: isHindi
        ? [
            "राष्ट्रीय-स्तरीय निगरानी",
            "राज्य एवं जिला प्रशासन",
            "अस्पताल अनुमोदन",
            "प्रणाली-व्यापी नियंत्रण",
          ]
        : [
            "National-level monitoring",
            "State and district administration",
            "Hospital approvals",
            "System-wide oversight",
          ],
      loginPath: "/portal/central/login",
      loginText: isHindi ? "केंद्रीय लॉगिन" : "Login to Central",
    },
  ];

  return (
    <div className="min-h-screen bg-[#F4F8FC] flex flex-col font-sans text-[#14243B]">
      <GovernmentHeader />

      {/* Breadcrumb Section */}
      <div className="bg-white border-b border-[#DCE5EF] py-3 px-4 sm:px-6">
        <div className="max-w-7xl mx-auto flex items-center justify-between text-xs">
          <div className="flex items-center gap-2 text-[#60738C]">
            <Link href="/" className="hover:text-[#0B2345] font-medium transition">
              {isHindi ? "होम" : "Home"}
            </Link>
            <ChevronRight className="w-3.5 h-3.5 text-[#60738C]/60" />
            <span className="text-[#14243B] font-semibold">
              {isHindi ? "विभागीय चयन" : "Department Selection"}
            </span>
          </div>

          <div className="flex items-center gap-1.5 text-[#60738C]">
            <Lock className="w-3.5 h-3.5 text-[#008F83]" />
            <span className="text-[11px] font-medium hidden sm:inline">
              {isHindi
                ? "स्वास्थ्य समन्वय • सुरक्षित स्वास्थ्य गेटवे"
                : "SWASTHYA SAMANVAY • Secured Health Gateway"}
            </span>
          </div>
        </div>
      </div>

      {/* Main Content Area */}
      <main className="flex-1 max-w-7xl mx-auto w-full px-4 sm:px-6 py-10 sm:py-14 space-y-10">
        {/* Page Header */}
        <div className="text-center max-w-3xl mx-auto space-y-3">
          <div className="inline-flex items-center gap-1.5 rounded-full bg-[#008F83]/10 border border-[#008F83]/20 px-3 py-1 text-xs font-bold text-[#008F83] tracking-wide uppercase">
            <Shield className="w-3.5 h-3.5 text-[#008F83]" />
            <span>
              {isHindi ? "अधिकृत स्वास्थ्य कर्मी पहुंच" : "Authorized Health Personnel Access"}
            </span>
          </div>
          <h1 className="text-2xl sm:text-4xl font-extrabold text-[#14243B] tracking-tight">
            {isHindi ? "अपने विभाग का चयन करें" : "Select Your Department"}
          </h1>
          <p className="text-sm sm:text-base text-[#60738C] leading-relaxed">
            {isHindi
              ? "पोर्टल में प्रवेश हेतु अपने अधिकृत विभाग का चयन करें। प्रत्येक विभाग विशिष्ट प्रशासनिक उपकरण, क्षेत्राधिकार डेटा पृथक्करण और लाइव संचालन डैशबोर्ड प्रदान करता है।"
              : "Choose your authorized department to access the portal. Each department provides tailored administrative tools, jurisdictional data isolation, and live operational dashboards."}
          </p>

          {currentUser && (
            <div className="mt-4 p-3.5 rounded-xl bg-[#008F83]/10 border border-[#008F83]/30 text-xs text-[#14243B] inline-flex items-center gap-2">
              <UserCheck className="w-4 h-4 text-[#008F83] shrink-0" />
              <span>
                {isHindi
                  ? `आप वर्तमान में ${currentUser.username} (${currentUser.role}) के रूप में लॉगिन हैं।`
                  : `You are currently signed in as ${currentUser.username} (${currentUser.role}).`}
              </span>
              <Link href="/" className="ml-2 underline font-bold text-[#008F83] hover:text-[#0B2345]">
                {isHindi ? "मेरे डैशबोर्ड पर जाएं →" : "Go to My Dashboard →"}
              </Link>
            </div>
          )}
        </div>

        {/* 4 Professional Department Cards Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
          {departments.map((dept) => {
            const Icon = dept.icon;
            return (
              <div
                key={dept.id}
                className="group relative flex flex-col justify-between rounded-xl bg-white border border-[#DCE5EF] p-6 shadow-xs hover:shadow-md hover:border-[#008F83]/40 transition duration-200 focus-within:ring-2 focus-within:ring-[#008F83] focus-within:ring-offset-2"
              >
                <div className="space-y-4">
                  {/* Top Bar: Icon + Tier Badge */}
                  <div className="flex items-center justify-between">
                    <div
                      className={`flex h-12 w-12 items-center justify-center rounded-xl border ${dept.iconColor} shadow-2xs transition group-hover:scale-105`}
                    >
                      <Icon className="w-6 h-6" />
                    </div>
                    <span
                      className={`rounded-full px-2.5 py-0.5 text-[10px] font-bold tracking-wider uppercase border ${dept.badgeColor}`}
                    >
                      {dept.tier}
                    </span>
                  </div>

                  {/* Title & Tagline */}
                  <div>
                    <h2 className="text-base sm:text-lg font-bold text-[#14243B] group-hover:text-[#008F83] transition">
                      {dept.title}
                    </h2>
                    <p className="text-[11px] font-semibold text-[#60738C] mt-0.5">
                      {dept.tagline}
                    </p>
                  </div>

                  {/* Description */}
                  <p className="text-xs text-[#60738C] leading-relaxed">
                    {dept.description}
                  </p>

                  {/* Key Features List */}
                  <div className="pt-2 border-t border-[#DCE5EF]/60 space-y-2">
                    <span className="text-[11px] font-bold uppercase tracking-wider text-[#60738C]/70">
                      {isHindi ? "मुख्य क्षमताएं:" : "Key Capabilities:"}
                    </span>
                    <ul className="space-y-1.5 text-xs text-[#14243B]">
                      {dept.features.map((feat) => (
                        <li key={feat} className="flex items-start gap-2">
                          <CheckCircle2 className="w-3.5 h-3.5 text-[#008F83] mt-0.5 shrink-0" />
                          <span>{feat}</span>
                        </li>
                      ))}
                    </ul>
                  </div>
                </div>

                {/* Bottom CTA Action Button */}
                <div className="pt-6 mt-4 border-t border-[#DCE5EF]/60">
                  <Link
                    href={dept.loginPath}
                    className={`w-full flex items-center justify-center gap-2 rounded-lg py-2.5 px-4 text-xs font-bold transition shadow-xs ${dept.buttonColor}`}
                  >
                    <span>{dept.loginText}</span>
                    <ArrowRight className="w-3.5 h-3.5 transition group-hover:translate-x-1" />
                  </Link>
                </div>
              </div>
            );
          })}
        </div>

        {/* Security & Access Information */}
        <div className="rounded-xl border border-[#DCE5EF] bg-white p-5 sm:p-6 shadow-xs flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
          <div className="flex items-start gap-3">
            <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-[#D99A27]/10 border border-[#D99A27]/30 text-[#D99A27]">
              <Shield className="w-5 h-5" />
            </div>
            <div>
              <h3 className="text-xs font-bold text-[#14243B] uppercase tracking-wide">
                {isHindi
                  ? "भूमिका-आधारित पहुंच नियंत्रण (RBAC) सूचना"
                  : "Role-Based Access Control (RBAC) Notice"}
              </h3>
              <p className="text-xs text-[#60738C] mt-0.5 max-w-2xl">
                {isHindi
                  ? "पहुंच केवल अधिकृत प्रशासनिक कर्मियों एवं प्रत्यायित स्वास्थ्य सेवा प्रदाताओं तक सीमित है। सभी उपयोगकर्ता सत्र और प्रणाली कार्य भूमिका-आधारित पहुंच नियंत्रण नीतियों के अनुसार प्रमाणित एवं ऑडिट किए जाते हैं।"
                  : "Access is restricted to authorized administrative personnel and accredited healthcare providers. User sessions and system actions are authenticated and audited in accordance with role-based access control policies."}
              </p>
            </div>
          </div>

          <div className="flex items-center gap-3 shrink-0">
            <Link
              href="/register/hospital"
              className="rounded-lg border border-[#DCE5EF] bg-[#F4F8FC] px-3.5 py-2 text-xs font-semibold text-[#14243B] hover:bg-[#DCE5EF]/50 transition"
            >
              {isHindi ? "अस्पताल पंजीकरण" : "Register Facility"}
            </Link>
            <Link
              href="/application/status"
              className="rounded-lg border border-[#DCE5EF] bg-[#F4F8FC] px-3.5 py-2 text-xs font-semibold text-[#14243B] hover:bg-[#DCE5EF]/50 transition"
            >
              {isHindi ? "आवेदन स्थिति" : "Track Status"}
            </Link>
          </div>
        </div>
      </main>

      <GovernmentFooter />
    </div>
  );
}