"use client";

import React from "react";
import Link from "next/link";
import {
  Building2,
  MapPin,
  ShieldCheck,
  Globe,
  ChevronRight,
  Shield,
  Layers,
  ArrowRight,
  CheckCircle2,
} from "lucide-react";
import { GovernmentHeader } from "@/components/shared/GovernmentHeader";
import { GovernmentFooter } from "@/components/shared/GovernmentFooter";
import { useLanguage } from "@/lib/i18n";

export default function JurisdictionalGovernancePage() {
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
              {isHindi ? "क्षेत्राधिकार शासन रूपरेखा" : "Jurisdictional Governance Framework"}
            </span>
          </div>

          <div className="flex items-center gap-1.5 text-indigo-700 font-medium text-[11px]">
            <Shield className="w-3.5 h-3.5 text-indigo-600" />
            <span>{isHindi ? "4-स्तरीय आधिकारिक पदानुक्रम" : "4-Tier Administrative Hierarchy"}</span>
          </div>
        </div>
      </div>

      {/* Page Header */}
      <section className="bg-gradient-to-b from-white to-slate-100 border-b border-slate-200 py-12 sm:py-16">
        <div className="max-w-4xl mx-auto px-4 sm:px-6 text-center space-y-4 animate-fade-in-up">
          <div className="inline-flex items-center gap-2 rounded-full bg-teal-50 border border-teal-200 px-3.5 py-1 text-xs font-bold text-teal-900 tracking-wide">
            <Layers className="w-3.5 h-3.5 text-teal-700" />
            <span>
              {isHindi ? "राष्ट्रीय स्वास्थ्य शासन" : "National Healthcare Governance"}
            </span>
          </div>

          <h1 className="text-3xl sm:text-4xl font-extrabold text-slate-950 tracking-tight">
            {isHindi ? "क्षेत्राधिकार शासन एवं प्रशासनिक पदानुक्रम" : "Jurisdictional Governance & Administrative Framework"}
          </h1>

          <p className="text-sm sm:text-base text-slate-600 max-w-2xl mx-auto leading-relaxed">
            {isHindi
              ? "अस्पताल से लेकर राष्ट्रीय स्तर तक डेटा पृथक्करण, चरणबद्ध अनुमोदन प्रक्रिया एवं सहयोगात्मक स्वास्थ्य शासन।"
              : "Institutional distribution of authority across facility operations, district administration, state health directorates, and apex central command."}
          </p>

          <div className="text-xs text-slate-500 pt-1">
            {isHindi ? "प्रशासनिक मानक • संस्करण 2.1" : "Administrative Standard • Version 2.1"}
          </div>
        </div>
      </section>

      {/* Main Content */}
      <main className="flex-1 max-w-4xl mx-auto px-4 sm:px-6 py-12 space-y-10">
        {/* Tier 1: Hospital Facility Operations */}
        <section className="rounded-2xl border border-slate-200 bg-white p-7 sm:p-8 space-y-4 shadow-xs card-hover-lift">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-blue-50 text-blue-700 border border-blue-200">
              <Building2 className="w-5 h-5" />
            </div>
            <div>
              <span className="text-[10px] font-bold uppercase tracking-wider text-blue-700">
                {isHindi ? "स्तर 1 • सुविधा स्तर" : "Tier 1 • Facility Jurisdiction"}
              </span>
              <h2 className="text-lg sm:text-xl font-bold text-slate-900">
                {isHindi ? "अस्पताल क्लिनिकल संचालन (Hospital Frontline)" : "Hospital Clinical Command & Operations"}
              </h2>
            </div>
          </div>
          <p className="text-xs sm:text-sm text-slate-600 leading-relaxed">
            {isHindi
              ? "अस्पताल स्तर पर अधिकृत चिकित्सा अधिकारी और नर्सिंग स्टाफ इनपेशेंट बेड का वास्तविक समय प्रबंधन करते हैं। नए मरीजों का इनटेक दर्ज करना, वर्तमान जीवन संकेतों के आधार पर स्थिति-आधारित रेफरल प्रेषित करना और आने वाले आपातकालीन मरीजों हेतु बेड आरक्षित करना इनका प्राथमिक दायित्व है।"
              : "At the primary operational level, frontline hospital clinicians and admissions officers maintain live bed counts (General, Oxygen, ICU). Attending physicians execute new patient intakes, evaluate critical vitals against algorithmic triage models, and trigger outbound transfers while holding bed reservations for arriving emergency ambulances."}
          </p>
          <div className="pt-2 text-xs text-slate-700 space-y-1.5 border-t border-slate-100">
            <div className="flex items-center gap-2">
              <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600 shrink-0" />
              <span>{isHindi ? "रोस्टर प्रबंधन एवं बेड आवंटन (सामान्य, ऑक्सीजन, आईसीयू)" : "Active bed inventory adjustment & atomic reservation hold"}</span>
            </div>
            <div className="flex items-center gap-2">
              <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600 shrink-0" />
              <span>{isHindi ? "आउटबाउंड रेफरल शुरुआत एवं इनबाउंड मरीज स्थानांतरण स्वीकृति" : "Outbound referral dispatch & inbound transfer confirmation"}</span>
            </div>
          </div>
        </section>

        {/* Tier 2: District Health Authority */}
        <section className="rounded-2xl border border-slate-200 bg-white p-7 sm:p-8 space-y-4 shadow-xs card-hover-lift">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-indigo-50 text-indigo-700 border border-indigo-200">
              <MapPin className="w-5 h-5" />
            </div>
            <div>
              <span className="text-[10px] font-bold uppercase tracking-wider text-indigo-700">
                {isHindi ? "स्तर 2 • जिला स्तर" : "Tier 2 • District Jurisdiction"}
              </span>
              <h2 className="text-lg sm:text-xl font-bold text-slate-900">
                {isHindi ? "जिला स्वास्थ्य प्राधिकरण (District Health Office)" : "District Health Authority & CMO Oversight"}
              </h2>
            </div>
          </div>
          <p className="text-xs sm:text-sm text-slate-600 leading-relaxed">
            {isHindi
              ? "मुख्य चिकित्सा अधिकारी (CMO) एवं जिला मजिस्ट्रेट के नेतृत्व में जिला स्वास्थ्य प्राधिकरण अपने क्षेत्राधिकार के सभी अस्पतालों की निगरानी करता है। नए अस्पताल ऑनबोर्डिंग आवेदनों की चरण-1 समीक्षा, क्लिनिकल प्रतिष्ठान प्रमाणपत्रों का सत्यापन एवं स्थानीय आपातकालीन सर्ज का समन्वय जिला स्तर पर होता है।"
              : "Under the leadership of the Chief Medical Officer (CMO) and District Magistrate, District Health Authorities monitor localized hospital utilization across their district. They conduct Stage-1 regulatory verification of hospital onboarding applications, verify clinical establishment certificates and physical bed counts, and coordinate emergency load redistribution during district surges."}
          </p>
          <div className="pt-2 text-xs text-slate-700 space-y-1.5 border-t border-slate-100">
            <div className="flex items-center gap-2">
              <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600 shrink-0" />
              <span>{isHindi ? "अस्पताल ऑनबोर्डिंग आवेदन की चरण-1 विनियामक समीक्षा" : "Stage-1 regulatory review of hospital onboarding dossiers"}</span>
            </div>
            <div className="flex items-center gap-2">
              <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600 shrink-0" />
              <span>{isHindi ? "जिला-स्तरीय बेड उपयोगिता एवं एम्बुलेंस समन्वय" : "District-wide bed utilization and emergency ambulance coordination"}</span>
            </div>
          </div>
        </section>

        {/* Tier 3: State Health Directorate */}
        <section className="rounded-2xl border border-slate-200 bg-white p-7 sm:p-8 space-y-4 shadow-xs card-hover-lift">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-teal-50 text-teal-700 border border-teal-200">
              <ShieldCheck className="w-5 h-5" />
            </div>
            <div>
              <span className="text-[10px] font-bold uppercase tracking-wider text-teal-700">
                {isHindi ? "स्तर 3 • राज्य स्तर" : "Tier 3 • State Jurisdiction"}
              </span>
              <h2 className="text-lg sm:text-xl font-bold text-slate-900">
                {isHindi ? "राज्य स्वास्थ्य निदेशालय (State Health Directorate)" : "State Health Directorate & Secondary Oversight"}
              </h2>
            </div>
          </div>
          <p className="text-xs sm:text-sm text-slate-600 leading-relaxed">
            {isHindi
              ? "राज्य स्वास्थ्य निदेशालय राज्य भर के जिलों की समग्र निगरानी करता है। जिला स्तर पर स्वीकृत आवेदनों की चरण-2 माध्यमिक समीक्षा, अंतर-जिला गंभीर मरीज स्थानांतरण, क्षेत्रीय मेडिकल कॉलेज हब समन्वय और संसाधन संतुलन का कार्य राज्य स्तर पर निष्पादित किया जाता है।"
              : "State Health Directorates oversee aggregate healthcare metrics across all constituent districts. They conduct Stage-2 secondary approval of hospital applications endorsed by districts, manage inter-district critical care transfers when localized district capacities are exhausted, and orchestrate resource deployment to apex medical colleges."}
          </p>
          <div className="pt-2 text-xs text-slate-700 space-y-1.5 border-t border-slate-100">
            <div className="flex items-center gap-2">
              <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600 shrink-0" />
              <span>{isHindi ? "चरण-2 माध्यमिक विनियामक अनुमोदन एवं नीतिगत अनुपालन" : "Stage-2 secondary application approval & policy compliance"}</span>
            </div>
            <div className="flex items-center gap-2">
              <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600 shrink-0" />
              <span>{isHindi ? "अंतर-जिला आपातकालीन मरीज सर्ज एवं तृतीयक केंद्र समन्वय" : "Inter-district patient surge balancing & tertiary institute triage"}</span>
            </div>
          </div>
        </section>

        {/* Tier 4: Central Health Authority */}
        <section className="rounded-2xl border border-slate-200 bg-white p-7 sm:p-8 space-y-4 shadow-xs card-hover-lift">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-purple-50 text-purple-700 border border-purple-200">
              <Globe className="w-5 h-5" />
            </div>
            <div>
              <span className="text-[10px] font-bold uppercase tracking-wider text-purple-700">
                {isHindi ? "स्तर 4 • राष्ट्रीय स्तर" : "Tier 4 • National Jurisdiction"}
              </span>
              <h2 className="text-lg sm:text-xl font-bold text-slate-900">
                {isHindi ? "केंद्रीय स्वास्थ्य कमान (Central Health Command)" : "Central Health Authority & Apex Governance"}
              </h2>
            </div>
          </div>
          <p className="text-xs sm:text-sm text-slate-600 leading-relaxed">
            {isHindi
              ? "राष्ट्रीय स्तर पर स्वास्थ्य मंत्रालय एवं केंद्रीय स्वास्थ्य प्राधिकरण समग्र देश में क्रिटिकल केयर टेलीमेट्री की निगरानी करते हैं। नए अस्पतालों को अंतिम चरण-3 अनुमोदन प्रदान कर सक्रियण टोकन जारी करना तथा राष्ट्रीय स्वास्थ्य मानकों का निर्धारण करना केंद्रीय कमान का दायित्व है।"
              : "The Central Health Authority represents the apex governing body. It maintains national health readiness telemetry, issues the final Stage-3 accreditation sign-off, triggers automated secure account provisioning for approved facilities, and enforces nationwide inter-hospital transfer protocols."}
          </p>
          <div className="pt-2 text-xs text-slate-700 space-y-1.5 border-t border-slate-100">
            <div className="flex items-center gap-2">
              <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600 shrink-0" />
              <span>{isHindi ? "अंतिम चरण-3 प्रत्यायन अनुमोदन एवं खाता सक्रियण प्रेषण" : "Final Stage-3 accreditation sign-off & account provisioning"}</span>
            </div>
            <div className="flex items-center gap-2">
              <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600 shrink-0" />
              <span>{isHindi ? "राष्ट्रव्यापी क्रिटिकल केयर तत्परता एवं आपदा प्रबंधन" : "Nationwide critical care surge coordination & disaster readiness"}</span>
            </div>
          </div>
        </section>

        {/* Explore Portals CTA */}
        <section className="rounded-2xl bg-[#0B132B] text-white p-6 sm:p-8 flex flex-col sm:flex-row items-center justify-between gap-6 shadow-md">
          <div className="space-y-1 text-center sm:text-left">
            <h3 className="text-base font-bold text-white">
              {isHindi ? "अपने प्रशासनिक पोर्टल में प्रवेश करें" : "Access Your Administrative Jurisdiction"}
            </h3>
            <p className="text-xs text-slate-300">
              {isHindi
                ? "अधिकृत स्वास्थ्य एवं प्रशासनिक पोर्टल में सुरक्षित रूप से साइन इन करें।"
                : "Sign in with your role-authorized credentials to enter your jurisdictional command."}
            </p>
          </div>

          <div className="flex items-center gap-3 shrink-0">
            <Link
              href="/portal"
              className="rounded-xl bg-teal-600 px-4 py-2.5 text-xs font-bold text-white hover:bg-teal-500 transition shadow-sm"
            >
              {isHindi ? "पोर्टल हब पर जाएं →" : "Explore Portals →"}
            </Link>
          </div>
        </section>
      </main>

      <GovernmentFooter />
    </div>
  );
}
