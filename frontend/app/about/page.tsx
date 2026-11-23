"use client";

import React from "react";
import Link from "next/link";
import {
  Building2,
  MapPin,
  ShieldCheck,
  Globe,
  Shield,
  HeartPulse,
  CheckCircle2,
} from "lucide-react";
import { GovernmentHeader } from "@/components/shared/GovernmentHeader";
import { GovernmentFooter } from "@/components/shared/GovernmentFooter";
import { useLanguage } from "@/lib/i18n";

export default function AboutPage() {
  const { isHindi } = useLanguage();

  return (
    <div className="min-h-screen bg-slate-50 text-slate-800 flex flex-col font-sans">
      <GovernmentHeader />

      {/* Page Header */}
      <section className="bg-gradient-to-b from-white to-slate-100 border-b border-slate-200 py-12 sm:py-16">
        <div className="max-w-5xl mx-auto px-4 sm:px-6 text-center space-y-4 animate-fade-in-up">
          <div className="inline-flex items-center gap-2 rounded-full bg-teal-50 border border-teal-200 px-3.5 py-1 text-xs font-bold text-teal-900 tracking-wide">
            <Shield className="w-3.5 h-3.5 text-teal-700" />
            <span>
              {isHindi ? "राष्ट्रीय स्वास्थ्य अवसंरचना" : "National Healthcare Infrastructure"}
            </span>
          </div>

          <h1 className="text-3xl sm:text-4xl font-extrabold text-slate-950 tracking-tight">
            {isHindi ? "स्वास्थ्य समन्वय के बारे में" : "About SWASTHYA SAMANVAY"}
          </h1>

          <p className="text-sm sm:text-base text-slate-600 max-w-3xl mx-auto leading-relaxed">
            {isHindi
              ? "भारत में क्रिटिकल केयर एवं आपातकालीन रेफरल में होने वाले विलंब को समाप्त करने हेतु समर्पित एक एकीकृत डिजिटल स्वास्थ्य समन्वय प्रणाली।"
              : "A unified digital healthcare coordination platform dedicated to eliminating critical care delays, transparently accounting for hospital beds, and orchestrating life-saving emergency patient transfers across India."}
          </p>
        </div>
      </section>

      {/* Main Content Body */}
      <main className="flex-1 max-w-6xl mx-auto px-4 sm:px-6 py-12 space-y-16">
        {/* Mission & Vision */}
        <section className="grid grid-cols-1 md:grid-cols-2 gap-8 items-stretch">
          <div className="rounded-2xl border border-slate-200 bg-white p-8 space-y-4 shadow-xs flex flex-col justify-between card-hover-lift">
            <div className="space-y-3">
              <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-teal-50 text-teal-700 border border-teal-200">
                <HeartPulse className="w-6 h-6" />
              </div>
              <h2 className="text-xl font-bold text-slate-900">
                {isHindi ? "हमारा लक्ष्य (Core Mission)" : "Our Core Mission"}
              </h2>
              <p className="text-xs sm:text-sm text-slate-600 leading-relaxed">
                {isHindi
                  ? "किसी भी गंभीर मरीज को बेड या वेंटिलेटर की कमी के कारण अस्पताल-दर-अस्पताल भटकना न पड़े। रीयल-टाइम बेड समन्वय और स्थिति-आधारित रेफरल द्वारा हर मरीज को सही समय पर सही अस्पताल में सुरक्षित प्रवेश दिलाना हमारा संकल्प है।"
                  : "To prevent tragic delays during critical emergencies by connecting frontline medical officers with live bed and ICU availability across participating hospitals. SWASTHYA SAMANVAY guarantees that when an ambulance leaves with a critical patient, a verified bed is already reserved and prepared at the destination facility."}
              </p>
            </div>
            <div className="pt-4 border-t border-slate-100 flex items-center gap-2 text-xs font-semibold text-teal-800">
              <CheckCircle2 className="w-4 h-4 text-emerald-600" />
              <span>
                {isHindi ? "शून्य-विलंब आपातकालीन स्थानांतरण" : "Zero-Delay Emergency Transfers"}
              </span>
            </div>
          </div>

          <div className="rounded-2xl border border-slate-200 bg-white p-8 space-y-4 shadow-xs flex flex-col justify-between card-hover-lift">
            <div className="space-y-3">
              <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-indigo-50 text-indigo-700 border border-indigo-200">
                <ShieldCheck className="w-6 h-6" />
              </div>
              <h2 className="text-xl font-bold text-slate-900">
                {isHindi ? "पारदर्शिता एवं सुशासन" : "Transparency & Governance"}
              </h2>
              <p className="text-xs sm:text-sm text-slate-600 leading-relaxed">
                {isHindi
                  ? "अस्पताल बेड इन्वेंट्री का परमाणु (Atomic) प्रबंधन, स्वचालित समाप्ति नियम और बहु-स्तरीय नियामक निगरानी के माध्यम से बिस्तरों की कृत्रिम होर्डिंग को रोकना तथा निष्पक्ष स्वास्थ्य पहुंच सुनिश्चित करना।"
                  : "Enforcing strict digital accountability across inpatient capacity. Automated expiry releases prevent arbitrary bed reservations, while multi-tier administrative surveillance ensures health resources are deployed equitably during both daily operations and regional surges."}
              </p>
            </div>
            <div className="pt-4 border-t border-slate-100 flex items-center gap-2 text-xs font-semibold text-indigo-800">
              <CheckCircle2 className="w-4 h-4 text-emerald-600" />
              <span>
                {isHindi ? "बेड होर्डिंग पर सख्त डिजिटल नियंत्रण" : "Strict Anti-Hoarding Bed Controls"}
              </span>
            </div>
          </div>
        </section>

        {/* 4-Tier Collaborative Governance */}
        <section className="space-y-8">
          <div className="text-center max-w-2xl mx-auto space-y-2">
            <span className="text-xs font-bold uppercase tracking-wider text-teal-800 bg-teal-50 border border-teal-200 px-3 py-1 rounded-full">
              {isHindi ? "सहयोगात्मक शासन" : "Multi-Tier Collaborative Governance"}
            </span>
            <h2 className="text-2xl sm:text-3xl font-extrabold text-slate-900 tracking-tight">
              {isHindi ? "4 प्रशासनिक स्तरों का निर्बाध समन्वय" : "Seamless Inter-Tier Collaboration"}
            </h2>
            <p className="text-xs sm:text-sm text-slate-500">
              {isHindi
                ? "अस्पताल से लेकर राष्ट्रीय स्तर तक डेटा सुरक्षा एवं क्षेत्राधिकार अलगाव के साथ एकीकृत प्रबंधन।"
                : "Every level operates with strict Role-Based Access Control and jurisdictional isolation."}
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
            <div className="rounded-2xl border border-slate-200 bg-white p-6 space-y-3 shadow-xs card-hover-lift">
              <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-teal-50 text-teal-800 border border-teal-200">
                <Building2 className="w-5 h-5" />
              </div>
              <h3 className="text-sm font-bold text-slate-900">
                {isHindi ? "1. अस्पताल अग्रिम पंक्ति" : "1. Hospital Frontline"}
              </h3>
              <p className="text-xs text-slate-600 leading-relaxed">
                {isHindi
                  ? "अग्रिम पंक्ति के डॉक्टर सक्रिय मरीज इनटेक का प्रबंधन करते हैं, रीयल-टाइम में बेड काउंटर अपडेट करते हैं और सीधी एम्बुलेंस रवानगी का समन्वय करते हैं।"
                  : "Frontline clinicians manage active patient intake, update bed counters in real-time, and coordinate direct ambulance dispatches."}
              </p>
            </div>

            <div className="rounded-2xl border border-slate-200 bg-white p-6 space-y-3 shadow-xs card-hover-lift">
              <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-indigo-50 text-indigo-800 border border-indigo-200">
                <MapPin className="w-5 h-5" />
              </div>
              <h3 className="text-sm font-bold text-slate-900">
                {isHindi ? "2. जिला स्वास्थ्य कार्यालय" : "2. District Health Office"}
              </h3>
              <p className="text-xs text-slate-600 leading-relaxed">
                {isHindi
                  ? "सीएमओ एवं जिला मजिस्ट्रेट स्थानीय क्षमता की निगरानी करते हैं, चरण-1 प्रत्यायन समीक्षा करते हैं और स्थानीय स्तर पर उत्पन्न बाधाओं का समाधान करते हैं।"
                  : "CMO & District Magistrates monitor local capacity, perform Stage-1 accreditation reviews, and resolve localized bottleneck alerts."}
              </p>
            </div>

            <div className="rounded-2xl border border-slate-200 bg-white p-6 space-y-3 shadow-xs card-hover-lift">
              <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-cyan-50 text-cyan-800 border border-cyan-200">
                <ShieldCheck className="w-5 h-5" />
              </div>
              <h3 className="text-sm font-bold text-slate-900">
                {isHindi ? "3. राज्य स्वास्थ्य निदेशालय" : "3. State Directorate"}
              </h3>
              <p className="text-xs text-slate-600 leading-relaxed">
                {isHindi
                  ? "राज्य स्वास्थ्य निदेशालय अंतर-जिला आपातकालीन सर्ज की निगरानी करते हैं, द्वितीयक समीक्षा को स्वीकृति देते हैं और क्षेत्रीय चिकित्सा संसाधनों का संतुलन बनाते हैं।"
                  : "State Health Directorates oversee inter-district patient surges, secondary dossier approvals, and regional medical resource balancing."}
              </p>
            </div>

            <div className="rounded-2xl border border-slate-200 bg-white p-6 space-y-3 shadow-xs card-hover-lift">
              <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-purple-50 text-purple-800 border border-purple-200">
                <Globe className="w-5 h-5" />
              </div>
              <h3 className="text-sm font-bold text-slate-900">
                {isHindi ? "4. केंद्रीय स्वास्थ्य प्राधिकरण" : "4. Central Authority"}
              </h3>
              <p className="text-xs text-slate-600 leading-relaxed">
                {isHindi
                  ? "शीर्ष स्वास्थ्य कमान राष्ट्रीय स्वास्थ्य टेलीमेट्री का अनुरक्षण, अंतिम चरण-3 प्रत्यायन अनुमोदन एवं राष्ट्रव्यापी तत्परता प्रोटोकॉल संचालित करते हैं।"
                  : "Apex health commands maintain national health telemetry, final Stage-3 accreditation sign-offs, and nationwide readiness protocols."}
              </p>
            </div>
          </div>
        </section>

        {/* Bottom CTA Card */}
        <section className="rounded-2xl bg-[#0B132B] text-white p-8 sm:p-10 flex flex-col sm:flex-row items-center justify-between gap-6 shadow-md">
          <div className="space-y-1 text-center sm:text-left">
            <h3 className="text-xl font-bold text-white">
              {isHindi ? "क्या आप एक स्वास्थ्य संस्थान हैं?" : "Are You an Accredited Healthcare Facility?"}
            </h3>
            <p className="text-xs sm:text-sm text-slate-300">
              {isHindi
                ? "राष्ट्रीय ग्रिड से जुड़कर अपने क्षेत्र में आपातकालीन स्वास्थ्य सेवाओं को सुदृढ़ करें।"
                : "Join the national coordination network to onboard your beds, receive verified referrals, and streamline critical care intake."}
            </p>
          </div>

          <div className="flex items-center gap-3 shrink-0">
            <Link
              href="/register/hospital"
              className="rounded-xl bg-teal-600 px-5 py-3 text-xs font-bold text-white hover:bg-teal-500 transition shadow-sm"
            >
              {isHindi ? "अस्पताल पंजीकृत करें →" : "Register Facility →"}
            </Link>
            <Link
              href="/contact"
              className="rounded-xl border border-slate-700 bg-slate-800/80 px-4 py-3 text-xs font-semibold text-slate-300 hover:bg-slate-700 transition"
            >
              {isHindi ? "संपर्क करें" : "Contact Helpdesk"}
            </Link>
          </div>
        </section>
      </main>

      <GovernmentFooter />
    </div>
  );
}
