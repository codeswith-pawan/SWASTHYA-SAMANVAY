"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import {
  Building2,
  MapPin,
  ShieldCheck,
  Globe,
  ArrowRight,
  Shield,
  PhoneCall,
  BedDouble,
  Activity,
  Ambulance,
  FileCheck2,
  ChevronRight,
  CheckCircle2,
  Lock,
  Hospital,
} from "lucide-react";
import HospitalDashboard from "@/components/HospitalDashboard";
import DistrictDashboard from "@/components/DistrictDashboard";
import StateDashboard from "@/components/StateDashboard";
import CentralDashboard from "@/components/CentralDashboard";
import { User } from "@/lib/types";
import { getStoredUser, clearStoredSession } from "@/lib/api";
import { LoadingState } from "@/components/shared/LoadingAndErrorStates";
import { GovernmentHeader } from "@/components/shared/GovernmentHeader";
import { GovernmentFooter } from "@/components/shared/GovernmentFooter";
import { useLanguage } from "@/lib/i18n";

export default function Home() {
  const [user, setUser] = useState<User | null>(null);
  const [mounted, setMounted] = useState(false);
  const { lang, setLang, isHindi } = useLanguage();

  // Restore authenticated session on page refresh
  useEffect(() => {
    setMounted(true);
    const stored = getStoredUser();
    if (stored) {
      setUser(stored);
    }
  }, []);

  const handleSignOut = () => {
    clearStoredSession();
    setUser(null);
  };

  if (!mounted) {
    return (
      <main className="min-h-screen bg-slate-50 flex items-center justify-center">
        <LoadingState message="Initializing healthcare session..." />
      </main>
    );
  }

  // Route to Authorized Tier Dashboard if authenticated
  if (user) {
    if (user.role === "HOSPITAL") {
      return <HospitalDashboard user={user} />;
    }
    if (user.role === "DISTRICT_ADMIN") {
      return <DistrictDashboard user={user} />;
    }
    if (user.role === "STATE_ADMIN") {
      return <StateDashboard user={user} />;
    }
    if (user.role === "CENTRAL_ADMIN") {
      return <CentralDashboard user={user} />;
    }

    return (
      <main className="min-h-screen bg-[#0B132B] text-slate-100 flex items-center justify-center p-6">
        <div className="rounded-2xl border border-slate-800 bg-[#0F172A] p-8 text-center max-w-md shadow-2xl">
          <h1 className="text-xl font-bold text-white">
            {isHindi ? "अपरिचित स्वास्थ्य सेवा भूमिका" : "Unrecognized Healthcare Role"}
          </h1>
          <p className="mt-2 text-xs text-slate-400">
            {isHindi
              ? `खाता ${user.username} (भूमिका ${user.role}) के पास सक्रिय डैशबोर्ड कॉन्फ़िगरेशन नहीं है।`
              : `Account ${user.username} with role ${user.role} does not have an active dashboard configuration.`}
          </p>
          <button
            onClick={handleSignOut}
            className="mt-5 rounded-lg bg-teal-600 px-4 py-2 text-xs font-semibold text-white hover:bg-teal-700 transition"
          >
            {isHindi ? "साइन आउट कर वापस जाएं" : "Sign Out & Return"}
          </button>
        </div>
      </main>
    );
  }

  return (
    <div className="min-h-screen bg-slate-50 text-slate-800 flex flex-col font-sans">
      <GovernmentHeader />

      {/* 1. Clean Hero Banner */}
      <section className="relative bg-gradient-to-b from-white via-slate-50 to-slate-100 border-b border-slate-200 py-16 sm:py-20 lg:py-24">
        <div className="max-w-5xl mx-auto px-4 sm:px-6 text-center space-y-6 animate-fade-in-up">
          {/* Subtle National Health Grid Badge */}
          <div className="inline-flex items-center gap-2 rounded-full bg-teal-50 border border-teal-200 px-3.5 py-1 text-xs font-bold text-teal-900 tracking-wide">
            <span className="flex h-2 w-2 rounded-full bg-emerald-500 animate-pulse-glow" />
            <span>
              {isHindi
                ? "राष्ट्रीय स्वास्थ्य सेवा समन्वय प्लेटफॉर्म"
                : "NATIONAL HEALTHCARE COORDINATION PLATFORM"}
            </span>
          </div>

          {/* Clear, Authoritative Headline */}
          <h1 className="text-3xl sm:text-5xl lg:text-5xl font-black text-slate-950 tracking-tight leading-[1.18] max-w-4xl mx-auto">
            {isHindi
              ? "अस्पतालों का जुड़ाव। देखभाल का समन्वय। समय की बचत।"
              : "Connecting Hospitals. Coordinating Care. Saving Time."}
          </h1>

          {/* Concise 2-line Description */}
          <p className="text-base sm:text-lg text-slate-600 leading-relaxed max-w-3xl mx-auto">
            {isHindi
              ? "अस्पतालों के संसाधनों के समन्वय, बेड उपलब्धता की दृश्यता, मरीज रेफरल को सुव्यवस्थित करने तथा अस्पतालों व स्वास्थ्य प्रशासनों के बीच सहयोग बढ़ाने के लिए डिज़ाइन किया गया एक एकीकृत डिजिटल प्लेटफॉर्म।"
              : "A unified digital platform designed to coordinate hospital resources, improve bed visibility, streamline patient referrals, and support collaboration between hospitals and healthcare administrations."}
          </p>

          {/* 3 Clear Action Buttons */}
          <div className="flex flex-wrap items-center justify-center gap-3.5 pt-4">
            <Link
              href="/register/hospital"
              className="rounded-xl bg-teal-700 px-6 py-3.5 text-sm font-bold text-white hover:bg-teal-800 transition shadow-sm flex items-center gap-2 btn-hover-lift"
            >
              <FileCheck2 className="w-4 h-4" />
              <span>{isHindi ? "अस्पताल पंजीकृत करें" : "Register Hospital"}</span>
            </Link>

            <Link
              href="/application/track"
              className="rounded-xl border border-slate-300 bg-white px-5 py-3.5 text-sm font-bold text-slate-700 hover:bg-slate-50 hover:border-slate-400 transition shadow-2xs flex items-center gap-2 btn-hover-lift"
            >
              <span>{isHindi ? "आवेदन ट्रैक करें" : "Track Application"}</span>
              <ChevronRight className="w-4 h-4 text-slate-400" />
            </Link>

            <Link
              href="/portal"
              className="rounded-xl bg-[#0B132B] px-6 py-3.5 text-sm font-bold text-white hover:bg-slate-800 transition shadow-sm flex items-center gap-2 btn-hover-lift"
            >
              <Lock className="w-4 h-4 text-teal-400" />
              <span>{isHindi ? "स्टाफ / विभाग लॉगिन" : "Staff / Department Login"}</span>
            </Link>
          </div>
        </div>
      </section>

      {/* 2. Quick Role Access Strip (4 Clean Cards) */}
      <section className="py-12 sm:py-16 bg-white border-b border-slate-200">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 space-y-8">
          <div className="text-center max-w-2xl mx-auto space-y-2">
            <span className="text-xs font-bold uppercase tracking-wider text-teal-800 bg-teal-50 border border-teal-200 px-3 py-1 rounded-full">
              {isHindi ? "विभागीय लॉगिन गेटवे" : "Departmental Sign-In Gateways"}
            </span>
            <h2 className="text-2xl sm:text-3xl font-extrabold text-slate-900 tracking-tight">
              {isHindi ? "अपने अधिकृत स्तर में प्रवेश करें" : "Access Your Healthcare Jurisdiction"}
            </h2>
            <p className="text-xs sm:text-sm text-slate-500">
              {isHindi
                ? "सख्त भूमिका-आधारित पहुंच नियंत्रण (RBAC) के साथ अपने निर्दिष्ट प्रशासनिक पोर्टल में साइन इन करें।"
                : "Secure, role-isolated portals for accredited medical personnel and public health administrators."}
            </p>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
            {/* 1. Hospital Staff */}
            <div className="rounded-2xl border border-slate-200 bg-slate-50/70 p-6 flex flex-col justify-between hover:border-teal-400 hover:shadow-md transition group card-hover-lift">
              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-teal-100 text-teal-800 border border-teal-200">
                    <Hospital className="w-5 h-5" />
                  </div>
                  <span className="rounded-full bg-teal-100 px-2.5 py-0.5 text-[10px] font-bold text-teal-800 uppercase tracking-wider">
                    {isHindi ? "सुविधा स्तर" : "Facility Tier"}
                  </span>
                </div>
                <h3 className="text-base font-bold text-slate-900 group-hover:text-teal-900 transition">
                  {isHindi ? "अस्पताल स्टाफ" : "Hospital Staff"}
                </h3>
                <p className="text-xs text-slate-600 leading-relaxed">
                  {isHindi
                    ? "बेड आवंटन, आईसीयू इन्वेंट्री, आपातकालीन इनटेक और मरीज रेफरल जीवन-चक्र का प्रबंधन।"
                    : "Bed accounting, ICU availability, emergency triage, and inbound/outbound referral lifecycles."}
                </p>
              </div>
              <div className="pt-5 mt-4 border-t border-slate-200">
                <Link
                  href="/portal/hospital/login"
                  className="w-full flex items-center justify-center gap-1.5 rounded-xl bg-[#0B132B] px-4 py-2.5 text-xs font-bold text-white hover:bg-teal-800 transition shadow-2xs btn-hover-lift"
                >
                  <span>{isHindi ? "अस्पताल लॉगिन" : "Hospital Login"}</span>
                  <ArrowRight className="w-3.5 h-3.5 text-teal-400" />
                </Link>
              </div>
            </div>

            {/* 2. District Health Office */}
            <div className="rounded-2xl border border-slate-200 bg-slate-50/70 p-6 flex flex-col justify-between hover:border-indigo-400 hover:shadow-md transition group card-hover-lift">
              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-indigo-100 text-indigo-800 border border-indigo-200">
                    <MapPin className="w-5 h-5" />
                  </div>
                  <span className="rounded-full bg-indigo-100 px-2.5 py-0.5 text-[10px] font-bold text-indigo-800 uppercase tracking-wider">
                    {isHindi ? "जिला स्तर" : "District Tier"}
                  </span>
                </div>
                <h3 className="text-base font-bold text-slate-900 group-hover:text-indigo-900 transition">
                  {isHindi ? "जिला स्वास्थ्य कार्यालय" : "District Health Office"}
                </h3>
                <p className="text-xs text-slate-600 leading-relaxed">
                  {isHindi
                    ? "जिला-स्तरीय अस्पताल निगरानी, चरण-1 प्रत्यायन समीक्षा और आपातकालीन समन्वय।"
                    : "District-wide facility surveillance, Stage-1 accreditation review, and localized coordination."}
                </p>
              </div>
              <div className="pt-5 mt-4 border-t border-slate-200">
                <Link
                  href="/portal/district/login"
                  className="w-full flex items-center justify-center gap-1.5 rounded-xl bg-indigo-900 px-4 py-2.5 text-xs font-bold text-white hover:bg-indigo-800 transition shadow-2xs btn-hover-lift"
                >
                  <span>{isHindi ? "जिला लॉगिन" : "District Login"}</span>
                  <ArrowRight className="w-3.5 h-3.5 text-indigo-300" />
                </Link>
              </div>
            </div>

            {/* 3. State Health Directorate */}
            <div className="rounded-2xl border border-slate-200 bg-slate-50/70 p-6 flex flex-col justify-between hover:border-cyan-400 hover:shadow-md transition group card-hover-lift">
              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-cyan-100 text-cyan-800 border border-cyan-200">
                    <ShieldCheck className="w-5 h-5" />
                  </div>
                  <span className="rounded-full bg-cyan-100 px-2.5 py-0.5 text-[10px] font-bold text-cyan-800 uppercase tracking-wider">
                    {isHindi ? "राज्य स्तर" : "State Tier"}
                  </span>
                </div>
                <h3 className="text-base font-bold text-slate-900 group-hover:text-cyan-900 transition">
                  {isHindi ? "राज्य स्वास्थ्य निदेशालय" : "State Health Directorate"}
                </h3>
                <p className="text-xs text-slate-600 leading-relaxed">
                  {isHindi
                    ? "राज्य-व्यापी क्षमता निगरानी, चरण-2 माध्यमिक अनुमोदन और अंतर-जिला संसाधन संतुलन।"
                    : "State-level critical care surveillance, Stage-2 secondary approval, and regional surge management."}
                </p>
              </div>
              <div className="pt-5 mt-4 border-t border-slate-200">
                <Link
                  href="/portal/state/login"
                  className="w-full flex items-center justify-center gap-1.5 rounded-xl bg-cyan-900 px-4 py-2.5 text-xs font-bold text-white hover:bg-cyan-800 transition shadow-2xs btn-hover-lift"
                >
                  <span>{isHindi ? "राज्य लॉगिन" : "State Login"}</span>
                  <ArrowRight className="w-3.5 h-3.5 text-cyan-300" />
                </Link>
              </div>
            </div>

            {/* 4. Central Health Authority */}
            <div className="rounded-2xl border border-slate-200 bg-slate-50/70 p-6 flex flex-col justify-between hover:border-purple-400 hover:shadow-md transition group card-hover-lift">
              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-purple-100 text-purple-800 border border-purple-200">
                    <Globe className="w-5 h-5" />
                  </div>
                  <span className="rounded-full bg-purple-100 px-2.5 py-0.5 text-[10px] font-bold text-purple-800 uppercase tracking-wider">
                    {isHindi ? "राष्ट्रीय स्तर" : "National Tier"}
                  </span>
                </div>
                <h3 className="text-base font-bold text-slate-900 group-hover:text-purple-900 transition">
                  {isHindi ? "केंद्रीय स्वास्थ्य प्राधिकरण" : "Central Health Authority"}
                </h3>
                <p className="text-xs text-slate-600 leading-relaxed">
                  {isHindi
                    ? "समग्र राष्ट्रीय स्वास्थ्य टेलीमेट्री, अंतिम चरण-3 प्रत्यायन अनुमोदन एवं नीतिगत नियंत्रण।"
                    : "National aggregate health telemetry, final Stage-3 accreditation sign-off, and apex policy oversight."}
                </p>
              </div>
              <div className="pt-5 mt-4 border-t border-slate-200">
                <Link
                  href="/portal/central/login"
                  className="w-full flex items-center justify-center gap-1.5 rounded-xl bg-purple-900 px-4 py-2.5 text-xs font-bold text-white hover:bg-purple-800 transition shadow-2xs btn-hover-lift"
                >
                  <span>{isHindi ? "केंद्रीय लॉगिन" : "Central Login"}</span>
                  <ArrowRight className="w-3.5 h-3.5 text-purple-300" />
                </Link>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* 3. Simple 3-Step "How It Works" Overview */}
      <section className="py-16 sm:py-20 bg-slate-50 border-b border-slate-200">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 space-y-12">
          <div className="text-center max-w-3xl mx-auto space-y-3">
            <span className="text-xs font-bold uppercase tracking-wider text-teal-800 bg-teal-100/60 border border-teal-200 px-3 py-1 rounded-full">
              {isHindi ? "कार्यप्रणाली" : "Simple Workflow"}
            </span>
            <h2 className="text-2xl sm:text-3xl font-extrabold text-slate-950 tracking-tight">
              {isHindi
                ? "यह कैसे काम करता है — 3 सरल चरण"
                : "How It Works — Simple 3-Step Process"}
            </h2>
            <p className="text-xs sm:text-sm text-slate-600 leading-relaxed">
              {isHindi
                ? "मरीजों को समय पर उपयुक्त बेड और विशेष उपचार उपलब्ध कराने की सरल व पारदर्शी प्रक्रिया।"
                : "A streamlined, transparent operational lifecycle ensuring zero transfer delays for critical patients."}
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
            {/* Step 1 */}
            <div className="rounded-2xl bg-white border border-slate-200 p-6 space-y-4 shadow-xs relative card-hover-lift">
              <div className="flex items-center justify-between">
                <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-teal-50 text-teal-700 border border-teal-200">
                  <BedDouble className="w-6 h-6" />
                </div>
                <span className="inline-flex h-8 w-8 items-center justify-center rounded-full bg-teal-100 text-teal-900 font-extrabold text-sm">
                  1
                </span>
              </div>
              <h3 className="text-base font-bold text-slate-900">
                {isHindi ? "रीयल-टाइम बेड ट्रैकिंग" : "Real-Time Bed Accounting"}
              </h3>
              <p className="text-xs text-slate-600 leading-relaxed">
                {isHindi
                  ? "पंजीकृत अस्पताल अपने सामान्य, ऑक्सीजन और आईसीयू बेड की वर्तमान उपलब्धता को नियमित रूप से अपडेट करते हैं।"
                  : "Accredited hospitals continuously report live general, oxygen, and ICU bed availability, eliminating blind patient transfers."}
              </p>
            </div>

            {/* Step 2 */}
            <div className="rounded-2xl bg-white border border-slate-200 p-6 space-y-4 shadow-xs relative card-hover-lift">
              <div className="flex items-center justify-between">
                <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-indigo-50 text-indigo-700 border border-indigo-200">
                  <Activity className="w-6 h-6" />
                </div>
                <span className="inline-flex h-8 w-8 items-center justify-center rounded-full bg-indigo-100 text-indigo-900 font-extrabold text-sm">
                  2
                </span>
              </div>
              <h3 className="text-base font-bold text-slate-900">
                {isHindi ? "स्थिति-आधारित रेफरल" : "Condition-Based Smart Referral"}
              </h3>
              <p className="text-xs text-slate-600 leading-relaxed">
                {isHindi
                  ? "मरीज की नैदानिक स्थिति, आवश्यक विशेषता और निकटता के आधार पर डॉक्टर उपयुक्त गंतव्य अस्पताल का चयन करते हैं।"
                  : "Attending clinicians initiate transfers matched against destination hospital specialties, live vitals, and geographical proximity."}
              </p>
            </div>

            {/* Step 3 */}
            <div className="rounded-2xl bg-white border border-slate-200 p-6 space-y-4 shadow-xs relative card-hover-lift">
              <div className="flex items-center justify-between">
                <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-emerald-50 text-emerald-700 border border-emerald-200">
                  <Ambulance className="w-6 h-6" />
                </div>
                <span className="inline-flex h-8 w-8 items-center justify-center rounded-full bg-emerald-100 text-emerald-900 font-extrabold text-sm">
                  3
                </span>
              </div>
              <h3 className="text-base font-bold text-slate-900">
                {isHindi ? "सुरक्षित स्थानांतरण व इनटेक" : "Fast Transit & Inbound Reception"}
              </h3>
              <p className="text-xs text-slate-600 leading-relaxed">
                {isHindi
                  ? "स्वीकृति मिलने पर बेड आरक्षित हो जाता है तथा एम्बुलेंस पहुंचने पर सीधे भर्ती प्रक्रिया पूरी की जाती है।"
                  : "Once accepted, bed capacity is atomically held and the receiving hospital prepares critical care staff before the ambulance arrives."}
              </p>
            </div>
          </div>

          {/* Learn More Multi-Page Link */}
          <div className="text-center pt-2">
            <Link
              href="/services"
              className="inline-flex items-center gap-1.5 text-xs font-bold text-teal-800 hover:text-teal-950 underline underline-offset-4"
            >
              <span>{isHindi ? "विस्तृत सेवाओं के बारे में जानें" : "Explore All Services & Capabilities"}</span>
              <ArrowRight className="w-3.5 h-3.5" />
            </Link>
          </div>
        </div>
      </section>

      {/* 4. Technical Support & Onboarding Assistance */}
      <section className="py-8 bg-white border-b border-slate-200">
        <div className="max-w-7xl mx-auto px-4 sm:px-6">
          <div className="rounded-2xl bg-[#0B132B] text-white p-6 sm:p-8 flex flex-col md:flex-row items-center justify-between gap-6 shadow-sm border border-slate-800">
            <div className="space-y-1 text-center md:text-left">
              <h3 className="text-lg font-bold text-white">
                {isHindi
                  ? "तकनीकी सहायता एवं ऑनबोर्डिंग परामर्श"
                  : "Technical Support & Hospital Onboarding"}
              </h3>
              <p className="text-xs text-slate-300">
                {isHindi
                  ? "अस्पताल पंजीकरण, बहु-स्तरीय अनुमोदन, अथवा क्रेडेंशियल सक्रियण हेतु हमारी तकनीकी टीम से संपर्क करें।"
                  : "Need assistance with facility onboarding, multi-tier accreditation, or credential activation? Reach our technical desk."}
              </p>
            </div>

            <div className="flex flex-wrap items-center justify-center gap-4 text-xs font-semibold">
              <a
                href="mailto:pawanbussiness108@gmail.com"
                className="flex items-center gap-2 bg-slate-900/90 px-4 py-2.5 rounded-xl border border-teal-500/30 hover:border-teal-400 text-teal-300 transition"
              >
                <span>pawanbussiness108@gmail.com</span>
              </a>
              <Link
                href="/application/track"
                className="flex items-center gap-1.5 bg-slate-800 px-4 py-2.5 rounded-xl border border-slate-700 text-slate-200 hover:text-white transition"
              >
                <span>{isHindi ? "आवेदन स्थिति" : "Track Application"}</span>
              </Link>
              <Link
                href="/contact"
                className="rounded-xl bg-teal-600 px-4 py-2.5 text-white font-bold hover:bg-teal-500 transition shadow-2xs"
              >
                {isHindi ? "सहायता केंद्र →" : "Helpdesk Details →"}
              </Link>
            </div>
          </div>
        </div>
      </section>

      <GovernmentFooter />
    </div>
  );
}
