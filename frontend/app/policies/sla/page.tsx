"use client";

import React from "react";
import Link from "next/link";
import {
  Clock,
  ChevronRight,
  Shield,
  Activity,
  Ambulance,
  PhoneCall,
  CheckCircle2,
  AlertCircle,
  Timer,
  Zap,
} from "lucide-react";
import { GovernmentHeader } from "@/components/shared/GovernmentHeader";
import { GovernmentFooter } from "@/components/shared/GovernmentFooter";
import { useLanguage } from "@/lib/i18n";

export default function InterHospitalSLAPage() {
  const { isHindi } = useLanguage();

  return (
    <div className="min-h-screen bg-slate-50 text-slate-800 flex flex-col font-sans">
      <GovernmentHeader />

      {/* Breadcrumbs */}
      <div className="bg-white border-b border-slate-200 py-3 px-4 sm:px-6">
        <div className="max-w-7xl mx-auto flex items-center justify-between text-xs">
          <div className="flex items-center gap-2 text-slate-500">
            <Link href="/" className="hover:text-teal-900 font-medium transition">
              {isHindi ? "होम" : "Home"}
            </Link>
            <ChevronRight className="w-3.5 h-3.5 text-slate-400" />
            <span className="text-slate-400">{isHindi ? "नीतियां" : "Policies"}</span>
            <ChevronRight className="w-3.5 h-3.5 text-slate-400" />
            <span className="text-slate-800 font-semibold">
              {isHindi ? "अंतर-अस्पताल सेवा स्तर मानक (SLA)" : "Inter-Hospital Service Level Agreements (SLA)"}
            </span>
          </div>

          <div className="flex items-center gap-1.5 text-emerald-700 font-medium text-[11px]">
            <Timer className="w-3.5 h-3.5 text-emerald-600" />
            <span>{isHindi ? "शून्य-विलंब आपातकालीन मानक" : "Zero-Delay Emergency Standards"}</span>
          </div>
        </div>
      </div>

      {/* Page Header */}
      <section className="bg-gradient-to-b from-white to-slate-100 border-b border-slate-200 py-12 sm:py-16">
        <div className="max-w-4xl mx-auto px-4 sm:px-6 text-center space-y-4 animate-fade-in-up">
          <div className="inline-flex items-center gap-2 rounded-full bg-teal-50 border border-teal-200 px-3.5 py-1 text-xs font-bold text-teal-900 tracking-wide">
            <Clock className="w-3.5 h-3.5 text-teal-700" />
            <span>
              {isHindi ? "परिचालन सेवा मानक" : "Operational Service Standards"}
            </span>
          </div>

          <h1 className="text-3xl sm:text-4xl font-extrabold text-slate-950 tracking-tight">
            {isHindi ? "अंतर-अस्पताल सेवा स्तर मानक (SLA)" : "Inter-Hospital Service Level Agreements (SLA)"}
          </h1>

          <p className="text-sm sm:text-base text-slate-600 max-w-2xl mx-auto leading-relaxed">
            {isHindi
              ? "क्रिटिकल केयर रेफरल, बेड आरक्षण अवधारण, एम्बुलेंस पारगमन और आपातकालीन एस्केलेशन हेतु बाध्यकारी समय सीमाएं।"
              : "Binding clinical response benchmarks, automated bed hold expiry policies, ambulance transit tracking, and 24/7 escalation protocols across the network."}
          </p>

          <div className="text-xs text-slate-500 pt-1">
            {isHindi ? "आधिकारिक परिचालन SLA • संस्करण 2.1" : "Official Operational SLA • Version 2.1"}
          </div>
        </div>
      </section>

      {/* Main Content */}
      <main className="flex-1 max-w-4xl mx-auto px-4 sm:px-6 py-12 space-y-10">
        {/* Benchmark 1: 30-Minute Automatic Bed Hold & Expiry */}
        <section className="rounded-2xl border border-slate-200 bg-white p-7 sm:p-8 space-y-4 shadow-xs card-hover-lift">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-teal-50 text-teal-700 border border-teal-200">
              <Timer className="w-5 h-5" />
            </div>
            <div>
              <span className="text-[10px] font-bold uppercase tracking-wider text-teal-700">
                {isHindi ? "बेड होर्डिंग रोकथाम" : "Anti-Hoarding Safeguard"}
              </span>
              <h2 className="text-lg sm:text-xl font-bold text-slate-900">
                {isHindi ? "1. 30 मिनट का स्वचालित बेड आरक्षण एवं स्वतः समाप्ति नियम" : "1. 30-Minute Automatic Bed Hold & Expiry Release"}
              </h2>
            </div>
          </div>
          <p className="text-xs sm:text-sm text-slate-600 leading-relaxed">
            {isHindi
              ? "जब गंतव्य अस्पताल किसी मरीज का रेफरल स्वीकार करता है, तो संबंधित बेड 30 मिनट के लिए परमाणु (Atomic) रूप से आरक्षित हो जाता है। यदि 30 मिनट के भीतर एम्बुलेंस रवानगी की पुष्टि नहीं होती अथवा मरीज नहीं पहुंचता, तो आरक्षित बेड स्वतः अवमुक्त हो जाता है ताकि अन्य जरूरतमंद गंभीर मरीज को बेड मिल सके।"
              : "Upon destination hospital acceptance of a transfer request, the targeted bed capacity (General, Oxygen, or ICU) is atomically held for exactly 30 minutes. If the referring facility fails to confirm ambulance dispatch ('IN_TRANSIT') or if the patient fails to arrive within the window, the reservation lock automatically releases back into public inventory to prevent phantom bed hoarding."}
          </p>
          <div className="p-3.5 rounded-xl bg-teal-50/70 border border-teal-200 text-xs text-teal-900 flex items-start gap-2.5">
            <Zap className="w-4 h-4 text-teal-700 shrink-0 mt-0.5" />
            <span>
              {isHindi
                ? "स्वचालित समय-समाप्ति नियम कृत्रिम बेड कमी को रोकता है और नेटवर्क में अधिकतम बिस्तरों का कुशल उपयोग सुनिश्चित करता है।"
                : "Automated row-level database locks guarantee zero overbooking and prevent artificial capacity hoarding during regional emergency peaks."}
            </span>
          </div>
        </section>

        {/* Benchmark 2: Referral Decision Windows */}
        <section className="rounded-2xl border border-slate-200 bg-white p-7 sm:p-8 space-y-4 shadow-xs card-hover-lift">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-indigo-50 text-indigo-700 border border-indigo-200">
              <Clock className="w-5 h-5" />
            </div>
            <div>
              <span className="text-[10px] font-bold uppercase tracking-wider text-indigo-700">
                {isHindi ? "निर्णय समय सीमा" : "Response Windows"}
              </span>
              <h2 className="text-lg sm:text-xl font-bold text-slate-900">
                {isHindi ? "2. क्लिनिकल ट्रायज एवं रेफरल निर्णय समय सीमाएं" : "2. Mandatory Referral Decision Windows"}
              </h2>
            </div>
          </div>
          <p className="text-xs sm:text-sm text-slate-600 leading-relaxed">
            {isHindi
              ? "मरीज की नैदानिक गंभीरता के आधार पर गंतव्य अस्पताल के लिए निर्णय लेने की समय सीमा निर्धारित है:"
              : "Receiving medical institutions must review and respond to incoming clinical referral requests within mandatory time windows based on patient acuity:"}
          </p>

          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 pt-2">
            <div className="p-4 rounded-xl bg-red-50 border border-red-200 space-y-1">
              <span className="text-[10px] font-bold uppercase tracking-wider text-red-700">
                {isHindi ? "गंभीर आपातकाल (Code Red)" : "Critical / Code Red"}
              </span>
              <h3 className="text-base font-extrabold text-red-950">≤ 15 {isHindi ? "मिनट" : "Minutes"}</h3>
              <p className="text-[11px] text-red-800 leading-snug">
                {isHindi ? "वेंटिलेटर, पॉलीट्रॉमा, तीव्र स्ट्रोक व कार्डियक अरेस्ट।" : "Severe respiratory failure, poly-trauma, acute stroke, and STEMI."}
              </p>
            </div>

            <div className="p-4 rounded-xl bg-amber-50 border border-amber-200 space-y-1">
              <span className="text-[10px] font-bold uppercase tracking-wider text-amber-700">
                {isHindi ? "अति-त्वरित (Urgent)" : "Urgent / High Priority"}
              </span>
              <h3 className="text-base font-extrabold text-amber-950">≤ 30 {isHindi ? "मिनट" : "Minutes"}</h3>
              <p className="text-[11px] text-amber-800 leading-snug">
                {isHindi ? "ऑक्सीजन समर्थन, तीव्र संक्रमण व आपातकालीन सर्जरी आवश्यकता।" : "Oxygen-dependent wards, acute infections, and emergency surgery intake."}
              </p>
            </div>

            <div className="p-4 rounded-xl bg-blue-50 border border-blue-200 space-y-1">
              <span className="text-[10px] font-bold uppercase tracking-wider text-blue-700">
                {isHindi ? "सामान्य रेफरल (Routine)" : "Standard Inpatient"}
              </span>
              <h3 className="text-base font-extrabold text-blue-950">≤ 60 {isHindi ? "मिनट" : "Minutes"}</h3>
              <p className="text-[11px] text-blue-800 leading-snug">
                {isHindi ? "स्थिर इनपेशेंट अवलोकन व विशेष नैदानिक परामर्श।" : "Stable transfers, diagnostic investigations, and sub-acute observation."}
              </p>
            </div>
          </div>
        </section>

        {/* Benchmark 3: Structured Transfer Lifecycle */}
        <section className="rounded-2xl border border-slate-200 bg-white p-7 sm:p-8 space-y-4 shadow-xs card-hover-lift">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-emerald-50 text-emerald-700 border border-emerald-200">
              <Ambulance className="w-5 h-5" />
            </div>
            <div>
              <span className="text-[10px] font-bold uppercase tracking-wider text-emerald-700">
                {isHindi ? "जीवन-चक्र ट्रैकिंग" : "Transit Lifecycle"}
              </span>
              <h2 className="text-lg sm:text-xl font-bold text-slate-900">
                {isHindi ? "3. संरचित रेफरल अवस्था चक्र (Referral Lifecycle)" : "3. Complete Five-Stage Referral State Machine"}
              </h2>
            </div>
          </div>
          <p className="text-xs sm:text-sm text-slate-600 leading-relaxed">
            {isHindi
              ? "प्रत्येक रेफरल को 5 स्पष्ट चरणों में ट्रैक किया जाता है ताकि दोनों अस्पतालों और एम्बुलेंस टीम के बीच पूर्ण समन्वय बना रहे:"
              : "To maintain continuous operational visibility, every patient referral progresses through a five-stage deterministic state machine:"}
          </p>

          <div className="grid grid-cols-1 sm:grid-cols-5 gap-3 pt-2 text-center text-xs">
            <div className="p-3 rounded-xl bg-slate-50 border border-slate-200">
              <span className="font-extrabold text-slate-800">1. PENDING</span>
              <p className="text-[10px] text-slate-500 mt-0.5">{isHindi ? "रेफरल प्रेषित" : "Transfer Initiated"}</p>
            </div>
            <div className="p-3 rounded-xl bg-indigo-50 border border-indigo-200">
              <span className="font-extrabold text-indigo-800">2. ACCEPTED</span>
              <p className="text-[10px] text-indigo-600 mt-0.5">{isHindi ? "बेड आरक्षित" : "Bed Held"}</p>
            </div>
            <div className="p-3 rounded-xl bg-teal-50 border border-teal-200">
              <span className="font-extrabold text-teal-800">3. IN_TRANSIT</span>
              <p className="text-[10px] text-teal-600 mt-0.5">{isHindi ? "एम्बुलेंस मार्ग में" : "Ambulance Dispatched"}</p>
            </div>
            <div className="p-3 rounded-xl bg-emerald-50 border border-emerald-200">
              <span className="font-extrabold text-emerald-800">4. ARRIVED</span>
              <p className="text-[10px] text-emerald-600 mt-0.5">{isHindi ? "गंतव्य पर आगमन" : "At Destination"}</p>
            </div>
            <div className="p-3 rounded-xl bg-purple-50 border border-purple-200">
              <span className="font-extrabold text-purple-800">5. COMPLETED</span>
              <p className="text-[10px] text-purple-600 mt-0.5">{isHindi ? "उपचार प्रारंभ" : "In Care"}</p>
            </div>
          </div>
        </section>

        {/* Benchmark 4: 24/7 National Emergency Escalation */}
        <section className="rounded-2xl border border-slate-200 bg-white p-7 sm:p-8 space-y-4 shadow-xs card-hover-lift">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-rose-50 text-rose-700 border border-rose-200">
              <PhoneCall className="w-5 h-5" />
            </div>
            <div>
              <span className="text-[10px] font-bold uppercase tracking-wider text-rose-700">
                {isHindi ? "आपातकालीन एस्केलेशन" : "24/7 Escalation"}
              </span>
              <h2 className="text-lg sm:text-xl font-bold text-slate-900">
                {isHindi ? "4. 24/7 आपातकालीन एस्केलेशन एवं हेल्पलाइन समन्वय" : "4. 24/7 National Emergency Escalation (108 & 1075)"}
              </h2>
            </div>
          </div>
          <p className="text-xs sm:text-sm text-slate-600 leading-relaxed">
            {isHindi
              ? "यदि किसी अति-गंभीर मरीज के लिए 15 मिनट में बेड स्वीकृति नहीं मिलती अथवा एम्बुलेंस मिलने में कठिनाई आती है, तो प्रणाली स्वचालित रूप से निकटतम वैकल्पिक अस्पतालों में अनुरोध अग्रेषित करती है। साथ ही 108 आपातकालीन एम्बुलेंस सेवा और जिला नियंत्रण कक्ष को तत्काल अलर्ट प्रेषित किया जाता है।"
              : "When a critical transfer request encounters no immediate acceptance within the 15-minute window or when regional transport bottlenecks arise, the system triggers automatic fallback matching to the next-nearest accredited facilities and alerts the 108 Emergency Ambulance dispatch center and the District CMO Emergency Cell for immediate administrative intervention."}
          </p>
        </section>

        {/* Contact Helpdesk Box */}
        <section className="rounded-2xl bg-[#0B132B] text-white p-6 sm:p-8 flex flex-col sm:flex-row items-center justify-between gap-6 shadow-md">
          <div className="space-y-1 text-center sm:text-left">
            <h3 className="text-base font-bold text-white">
              {isHindi ? "SLA अनुपालन अथवा परिचालन सहायता" : "SLA Inquiries & Operational Assistance"}
            </h3>
            <p className="text-xs text-slate-300">
              {isHindi
                ? "सेवा स्तर मानकों अथवा अंतर-अस्पताल प्रोटोकॉल हेतु हमारे सहायता केंद्र से संपर्क करें।"
                : "For SLA inquiries, dispatch coordination, or incident reports, reach out to our team."}
            </p>
          </div>

          <div className="flex items-center gap-3 shrink-0">
            <Link
              href="/contact"
              className="rounded-xl bg-teal-600 px-4 py-2.5 text-xs font-bold text-white hover:bg-teal-500 transition shadow-sm"
            >
              {isHindi ? "सहायता केंद्र विवरण" : "Contact Helpdesk"}
            </Link>
          </div>
        </section>
      </main>

      <GovernmentFooter />
    </div>
  );
}
