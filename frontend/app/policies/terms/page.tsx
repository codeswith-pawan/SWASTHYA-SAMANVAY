"use client";

import React from "react";
import Link from "next/link";
import {
  FileText,
  ChevronRight,
  CheckCircle2,
  AlertTriangle,
  Stethoscope,
  Scale,
  Shield,
  Hospital,
} from "lucide-react";
import { GovernmentHeader } from "@/components/shared/GovernmentHeader";
import { GovernmentFooter } from "@/components/shared/GovernmentFooter";
import { useLanguage } from "@/lib/i18n";

export default function TermsOfServicePage() {
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
              {isHindi ? "सेवा की शर्तें (Terms of Service)" : "Terms of Service"}
            </span>
          </div>

          <div className="flex items-center gap-1.5 text-slate-600 text-[11px] font-medium">
            <Scale className="w-3.5 h-3.5 text-teal-600" />
            <span>{isHindi ? "आधिकारिक परिचालन समझौता" : "Official Operational Agreement"}</span>
          </div>
        </div>
      </div>

      {/* Page Header */}
      <section className="bg-gradient-to-b from-white to-slate-100 border-b border-slate-200 py-12 sm:py-16">
        <div className="max-w-4xl mx-auto px-4 sm:px-6 text-center space-y-4 animate-fade-in-up">
          <div className="inline-flex items-center gap-2 rounded-full bg-teal-50 border border-teal-200 px-3.5 py-1 text-xs font-bold text-teal-900 tracking-wide">
            <FileText className="w-3.5 h-3.5 text-teal-700" />
            <span>
              {isHindi ? "संस्थागत परिचालन समझौता" : "Institutional Operating Agreement"}
            </span>
          </div>

          <h1 className="text-3xl sm:text-4xl font-extrabold text-slate-950 tracking-tight">
            {isHindi ? "सेवा की शर्तें एवं उपयोग नियम" : "Terms of Service & Operational Rules"}
          </h1>

          <p className="text-sm sm:text-base text-slate-600 max-w-2xl mx-auto leading-relaxed">
            {isHindi
              ? "आरोग्यसेतु ग्रिड पर संबद्ध अस्पतालों, चिकित्सा अधिकारियों और स्वास्थ्य निदेशालयों हेतु परिचालन नियम एवं कानूनी दायित्व।"
              : "Mandatory operating standards and institutional terms governing accredited medical centers, attending physicians, and public health authorities utilizing the portal."}
          </p>

          <div className="text-xs text-slate-500 pt-1">
            {isHindi ? "प्रभावी तिथि: नवंबर 2026 • आधिकारिक संस्करण" : "Effective Date: November 2026 • Official Version"}
          </div>
        </div>
      </section>

      {/* Main Content */}
      <main className="flex-1 max-w-4xl mx-auto px-4 sm:px-6 py-12 space-y-10">
        {/* Section 1: Accurate Real-Time Bed Reporting */}
        <section className="rounded-2xl border border-slate-200 bg-white p-7 sm:p-8 space-y-4 shadow-xs card-hover-lift">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-teal-50 text-teal-700 border border-teal-200">
              <Hospital className="w-5 h-5" />
            </div>
            <h2 className="text-lg sm:text-xl font-bold text-slate-900">
              {isHindi ? "1. रीयल-टाइम बेड रिपोर्टिंग की अनिवार्यता एवं सत्यनिष्ठा" : "1. Mandatory Truth-in-Reporting for Bed Inventory"}
            </h2>
          </div>
          <p className="text-xs sm:text-sm text-slate-600 leading-relaxed">
            {isHindi
              ? "प्रत्येक संबद्ध अस्पताल का यह विधिक दायित्व है कि वह अपने सामान्य, ऑक्सीजन एवं आईसीयू बिस्तरों की वास्तविक उपलब्धता को सटीक रूप से अद्यतन रखे। कृत्रिम रूप से बिस्तरों की कमी दिखाना या बेड होर्डिंग करना गंभीर विनियामक उल्लंघन माना जाएगा और इसके परिणामस्वरूप अस्पताल का प्रत्यायन निलंबित किया जा सकता है।"
              : "Accredited hospitals undertake a binding commitment to maintain active, accurate reporting of inpatient general, oxygen-supported, and ICU bed availability. Fictitious capacity reporting, artificial bed suppression, or intentional delay in recording bed vacancies constitutes a material regulatory violation subject to immediate credential suspension and district inspection."}
          </p>
        </section>

        {/* Section 2: Clinical Decision Support & Physician Primacy */}
        <section className="rounded-2xl border border-slate-200 bg-white p-7 sm:p-8 space-y-4 shadow-xs card-hover-lift">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-indigo-50 text-indigo-700 border border-indigo-200">
              <Stethoscope className="w-5 h-5" />
            </div>
            <h2 className="text-lg sm:text-xl font-bold text-slate-900">
              {isHindi ? "2. क्लिनिकल निर्णय समर्थन एवं डॉक्टर का अंतिम विवेक" : "2. Clinical Decision Support Disclaimer & Physician Primacy"}
            </h2>
          </div>
          <p className="text-xs sm:text-sm text-slate-600 leading-relaxed">
            {isHindi
              ? "स्वास्थ्य समन्वय का एल्गोरिथम रेफरल इंजन दूरी, जीवन संकेत और विशेषज्ञता के आधार पर सक्षम अस्पतालों की सिफारिश करता है। यह प्रणाली चिकित्सकीय परामर्श का विकल्प नहीं है। मरीज के स्थानांतरण और उपचार का अंतिम निर्णय सदैव उपस्थित पंजीकृत चिकित्सा अधिकारी (RMO) के विवेक पर निर्भर होगा।"
              : "Algorithmic triage scores and destination hospital proximity recommendations provided by SWASTHYA SAMANVAY serve purely as clinical decision-support aids. The system does not practice medicine. The decision to initiate an inter-facility transfer, select a destination hospital, and dispatch emergency transport remains the sole professional responsibility of the attending Registered Medical Officer (RMO)."}
          </p>
        </section>

        {/* Section 3: Credential Security & Prohibited Conduct */}
        <section className="rounded-2xl border border-slate-200 bg-white p-7 sm:p-8 space-y-4 shadow-xs card-hover-lift">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-amber-50 text-amber-700 border border-amber-200">
              <AlertTriangle className="w-5 h-5" />
            </div>
            <h2 className="text-lg sm:text-xl font-bold text-slate-900">
              {isHindi ? "3. क्रेडेंशियल सुरक्षा एवं प्रतिबंधित आचरण" : "3. Credential Security & Prohibited Activities"}
            </h2>
          </div>
          <p className="text-xs sm:text-sm text-slate-600 leading-relaxed">
            {isHindi
              ? "अधिकृत नोडल अधिकारियों एवं चिकित्सा कर्मियों को अपने लॉगिन क्रेडेंशियल को सुरक्षित रखना अनिवार्य है। खातों को साझा करना, प्रणाली की सुरक्षा जांच को बायपास करने का प्रयास करना अथवा अनधिकृत डेटा निष्कर्षण करना सख्त वर्जित है।"
              : "Authorized institutional personnel must maintain the strict confidentiality of their departmental credentials. User account sharing across multiple staff members is prohibited. Any attempt to probe backend endpoints, bypass rate limits, inject unverified medical claims, or scrape network telemetry will trigger automatic session termination and regulatory reporting."}
          </p>
        </section>

        {/* Section 4: Compliance with Regulatory Frameworks */}
        <section className="rounded-2xl border border-slate-200 bg-white p-7 sm:p-8 space-y-4 shadow-xs card-hover-lift">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-purple-50 text-purple-700 border border-purple-200">
              <Scale className="w-5 h-5" />
            </div>
            <h2 className="text-lg sm:text-xl font-bold text-slate-900">
              {isHindi ? "4. वैधानिक अनुपालन एवं प्रत्यायन नवीनीकरण" : "4. Statutory Compliance & Accreditation Lifecycle"}
            </h2>
          </div>
          <p className="text-xs sm:text-sm text-slate-600 leading-relaxed">
            {isHindi
              ? "संबद्ध अस्पतालों को क्लिनिकल एस्टेब्लिशमेंट एक्ट, राज्य स्वास्थ्य नियमों, अग्नि सुरक्षा प्रमाणपत्र (Fire NOC) और बायो-मेडिकल वेस्ट प्रबंधन मानकों का निरंतर पालन करना आवश्यक है। प्रमाणपत्रों की वैधता समाप्त होने पर पोर्टल पहुंच अस्थायी रूप से निलंबित की जा सकती है।"
              : "Participation in the network is contingent upon continuous compliance with state Clinical Establishment Acts, up-to-date Fire Safety NOCs, and environmental Bio-Medical Waste clearances. Facilities are obligated to upload renewed compliance certificates before expiration to maintain active booking privileges."}
          </p>
        </section>

        {/* Action Link to Support */}
        <section className="rounded-2xl bg-[#0B132B] text-white p-6 sm:p-8 flex flex-col sm:flex-row items-center justify-between gap-6 shadow-md">
          <div className="space-y-1 text-center sm:text-left">
            <h3 className="text-base font-bold text-white">
              {isHindi ? "परिचालन शर्तों के संबंध में प्रश्न?" : "Questions Regarding Institutional Terms?"}
            </h3>
            <p className="text-xs text-slate-300">
              {isHindi
                ? "प्रत्यायन नियमों अथवा परिचालन समझौतों के लिए हमारी कानूनी सहायता टीम से संपर्क करें।"
                : "For compliance clarification or institutional agreements, contact our administrative desk."}
            </p>
          </div>

          <div className="flex items-center gap-3 shrink-0">
            <Link
              href="/contact"
              className="rounded-xl bg-teal-600 px-4 py-2.5 text-xs font-bold text-white hover:bg-teal-500 transition shadow-sm"
            >
              {isHindi ? "सहायता केंद्र से संपर्क करें" : "Contact Helpdesk"}
            </Link>
          </div>
        </section>
      </main>

      <GovernmentFooter />
    </div>
  );
}
