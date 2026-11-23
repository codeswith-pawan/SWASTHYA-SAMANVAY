"use client";

import React from "react";
import Link from "next/link";
import {
  ShieldCheck,
  Lock,
  ChevronRight,
  Database,
  FileCheck2,
  Users,
  AlertCircle,
  Clock,
  ArrowRight,
} from "lucide-react";
import { GovernmentHeader } from "@/components/shared/GovernmentHeader";
import { GovernmentFooter } from "@/components/shared/GovernmentFooter";
import { useLanguage } from "@/lib/i18n";

export default function SecurityPolicyPage() {
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
              {isHindi ? "सुरक्षा एवं डेटा गोपनीयता नीति" : "Security & Data Privacy Policy"}
            </span>
          </div>

          <div className="flex items-center gap-1.5 text-emerald-700 font-medium text-[11px]">
            <Lock className="w-3.5 h-3.5 text-emerald-600" />
            <span>{isHindi ? "सख्त डेटा सुरक्षा अनुपालन" : "Clinical Data Security Compliant"}</span>
          </div>
        </div>
      </div>

      {/* Page Header */}
      <section className="bg-gradient-to-b from-white to-slate-100 border-b border-slate-200 py-12 sm:py-16">
        <div className="max-w-4xl mx-auto px-4 sm:px-6 text-center space-y-4 animate-fade-in-up">
          <div className="inline-flex items-center gap-2 rounded-full bg-teal-50 border border-teal-200 px-3.5 py-1 text-xs font-bold text-teal-900 tracking-wide">
            <ShieldCheck className="w-3.5 h-3.5 text-teal-700" />
            <span>
              {isHindi ? "आधिकारिक विनियामक मानक" : "Official Regulatory Standard"}
            </span>
          </div>

          <h1 className="text-3xl sm:text-4xl font-extrabold text-slate-950 tracking-tight">
            {isHindi ? "सुरक्षा एवं डेटा गोपनीयता नीति" : "Security & Patient Privacy Policy"}
          </h1>

          <p className="text-sm sm:text-base text-slate-600 max-w-2xl mx-auto leading-relaxed">
            {isHindi
              ? "आरोग्यसेतु ग्रिड पर प्रबंधित क्रिटिकल केयर डेटा, मरीज पहचान, बेड आरक्षण एवं अंतर-अस्पताल रेफरल हेतु कड़े सुरक्षा मानक।"
              : "Institutional protocols governing clinical telemetry security, Role-Based Access Control, encrypted audit logging, and patient privacy safeguards across the network."}
          </p>

          <div className="text-xs text-slate-500 pt-1">
            {isHindi ? "प्रभावी तिथि: नवंबर 2026 • संस्करण 2.1" : "Effective Date: November 2026 • Version 2.1"}
          </div>
        </div>
      </section>

      {/* Main Content */}
      <main className="flex-1 max-w-4xl mx-auto px-4 sm:px-6 py-12 space-y-10">
        {/* Section 1: Role-Based Access Control */}
        <section className="rounded-2xl border border-slate-200 bg-white p-7 sm:p-8 space-y-4 shadow-xs card-hover-lift">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-teal-50 text-teal-700 border border-teal-200">
              <Users className="w-5 h-5" />
            </div>
            <h2 className="text-lg sm:text-xl font-bold text-slate-900">
              {isHindi ? "1. भूमिका-आधारित पहुंच नियंत्रण (RBAC) एवं क्षेत्राधिकार अलगाव" : "1. Role-Based Access Control (RBAC) & Jurisdictional Isolation"}
            </h2>
          </div>
          <p className="text-xs sm:text-sm text-slate-600 leading-relaxed">
            {isHindi
              ? "प्रत्येक अधिकृत उपयोगकर्ता को उनके प्रशासनिक दायित्व के अनुसार सख्त क्षेत्राधिकार में सीमित रखा जाता है। अस्पताल केवल अपने मरीज और बेड का डेटा देख सकते हैं, जिला अधिकारी केवल अपने जिले के अस्पतालों की समीक्षा कर सकते हैं, तथा राज्य एवं केंद्र अधिकारी समग्र विश्लेषिकी का अवलोकन करते हैं।"
              : "Access to SWASTHYA SAMANVAY is strictly partitioned by institutional hierarchy. Hospital personnel can only manipulate bed counters and referrals within their accredited facility; District CMOs are restricted to facilities within their administrative district; and State/Central Directorates possess aggregate telemetry privileges without cross-facility clinical record leakage."}
          </p>
          <ul className="space-y-2 text-xs text-slate-700 pt-2 border-t border-slate-100">
            <li className="flex items-start gap-2">
              <div className="h-1.5 w-1.5 rounded-full bg-teal-600 mt-1.5 shrink-0" />
              <span>
                {isHindi
                  ? "अस्पताल स्टाफ (HOSPITAL): बेड इन्वेंट्री अद्यतन, नए मरीज पंजीकरण एवं स्थिति-आधारित रेफरल प्रेषण।"
                  : "Hospital Staff (HOSPITAL): Real-time bed updating, patient intake, and condition-based referral initiation."}
              </span>
            </li>
            <li className="flex items-start gap-2">
              <div className="h-1.5 w-1.5 rounded-full bg-teal-600 mt-1.5 shrink-0" />
              <span>
                {isHindi
                  ? "जिला स्वास्थ्य प्राधिकरण (DISTRICT_ADMIN): चरण-1 प्रत्यायन समीक्षा, भौतिक सत्यापन एवं जिला-स्तरीय समन्वय।"
                  : "District Administration (DISTRICT_ADMIN): Stage-1 accreditation review, compliance audits, and district coordination."}
              </span>
            </li>
            <li className="flex items-start gap-2">
              <div className="h-1.5 w-1.5 rounded-full bg-teal-600 mt-1.5 shrink-0" />
              <span>
                {isHindi
                  ? "राज्य स्वास्थ्य निदेशालय (STATE_ADMIN): चरण-2 द्वितीयक अनुमोदन एवं अंतर-जिला संसाधन संतुलन।"
                  : "State Directorate (STATE_ADMIN): Stage-2 secondary approvals, regional surge monitoring, and resource balancing."}
              </span>
            </li>
            <li className="flex items-start gap-2">
              <div className="h-1.5 w-1.5 rounded-full bg-teal-600 mt-1.5 shrink-0" />
              <span>
                {isHindi
                  ? "केंद्रीय स्वास्थ्य प्राधिकरण (CENTRAL_ADMIN): अंतिम चरण-3 प्रत्यायन अनुमोदन एवं राष्ट्रीय स्वास्थ्य टेलीमेट्री निगरानी।"
                  : "Central Command (CENTRAL_ADMIN): Final Stage-3 accreditation sign-off and national healthcare policy surveillance."}
              </span>
            </li>
          </ul>
        </section>

        {/* Section 2: Authentication & 2FA */}
        <section className="rounded-2xl border border-slate-200 bg-white p-7 sm:p-8 space-y-4 shadow-xs card-hover-lift">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-indigo-50 text-indigo-700 border border-indigo-200">
              <Lock className="w-5 h-5" />
            </div>
            <h2 className="text-lg sm:text-xl font-bold text-slate-900">
              {isHindi ? "2. नोडल अधिकारी प्रमाणीकरण एवं दो-चरणीय सत्यापन (2FA)" : "2. Nodal Officer Authentication & Two-Factor Verification"}
            </h2>
          </div>
          <p className="text-xs sm:text-sm text-slate-600 leading-relaxed">
            {isHindi
              ? "अनधिकृत पहुंच को रोकने हेतु सभी ऑनबोर्डिंग और प्रशासनिक खातों का सत्यापन अधिकृत सरकारी/संस्थागत ईमेल पते पर प्रेषित समय-सीमित वन-टाइम पासवर्ड (OTP) द्वारा किया जाता है। सत्र प्रबंधन क्रिप्टोग्राफिक रूप से हस्ताक्षरित JWT टोकन द्वारा सुरक्षित है।"
              : "To prevent fraudulent facility claims and unauthorized administrative access, all onboarding applications require mandatory two-factor email verification of the designated Nodal Officer. Authenticated sessions utilize cryptographically signed JSON Web Tokens (JWT) with strict timeout windows and continuous session revocation capabilities."}
          </p>
        </section>

        {/* Section 3: Immutable Audit Logging */}
        <section className="rounded-2xl border border-slate-200 bg-white p-7 sm:p-8 space-y-4 shadow-xs card-hover-lift">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-cyan-50 text-cyan-700 border border-cyan-200">
              <Database className="w-5 h-5" />
            </div>
            <h2 className="text-lg sm:text-xl font-bold text-slate-900">
              {isHindi ? "3. अपरिवर्तनीय ऑडिट ट्रेल एवं बेड आरक्षण लॉग" : "3. Immutable Audit Trails & Reservation Logging"}
            </h2>
          </div>
          <p className="text-xs sm:text-sm text-slate-600 leading-relaxed">
            {isHindi
              ? "प्रत्येक मरीज इनटेक, रेफरल स्वीकृति, स्थिति परिवर्तन और बेड आवंटन का पूर्ण इतिहास टाइमस्टैम्प, उपयोगकर्ता आईडी और आईपी पते के साथ स्थायी रूप से रिकॉर्ड किया जाता है। किसी भी रिकॉर्ड को मिटाया या संशोधित नहीं किया जा सकता, जिससे पूर्ण प्रशासनिक जवाबदेही सुनिश्चित होती है।"
              : "Every clinical transfer state transition, bed increment/decrement, and application sign-off produces an immutable audit record containing precise timestamps, user identifiers, and operational notes. This eliminates arbitrary bed cancellation disputes and guarantees forensic auditability during regulatory compliance reviews."}
          </p>
        </section>

        {/* Section 4: Patient Privacy & Data Handling */}
        <section className="rounded-2xl border border-slate-200 bg-white p-7 sm:p-8 space-y-4 shadow-xs card-hover-lift">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-purple-50 text-purple-700 border border-purple-200">
              <FileCheck2 className="w-5 h-5" />
            </div>
            <h2 className="text-lg sm:text-xl font-bold text-slate-900">
              {isHindi ? "4. मरीज डेटा सुरक्षा एवं न्यूनतम आवश्यकता सिद्धांत" : "4. Patient Privacy & Data Minimization"}
            </h2>
          </div>
          <p className="text-xs sm:text-sm text-slate-600 leading-relaxed">
            {isHindi
              ? "रेफरल के दौरान केवल आपातकालीन ट्रायज और बेड उपयुक्तता हेतु आवश्यक न्यूनतम नैदानिक जानकारी (जैसे GCS, SpO2, मुख्य शिकायत व विशेषता आवश्यकता) ही साझा की जाती है। सभी डेटा संचार टीएलएस 1.3 एन्क्रिप्शन द्वारा सुरक्षित हैं।"
              : "In accordance with national healthcare privacy standards, only clinically necessary telemetry (vital signs, Glasgow Coma Scale, oxygen saturation, and provisional diagnoses) is transmitted to the prospective receiving hospital to evaluate capacity. Non-clinical identifiers are shielded, and all in-transit network traffic is enforced via modern TLS 1.3 encryption."}
          </p>
        </section>

        {/* Security Helpdesk Box */}
        <section className="rounded-2xl bg-[#0B132B] text-white p-6 sm:p-8 flex flex-col sm:flex-row items-center justify-between gap-6 shadow-md">
          <div className="space-y-1 text-center sm:text-left">
            <h3 className="text-base font-bold text-white">
              {isHindi ? "सुरक्षा संबंधी पूछताछ अथवा रिपोर्ट" : "Security Inquiries & Vulnerability Reporting"}
            </h3>
            <p className="text-xs text-slate-300">
              {isHindi
                ? "किसी भी सुरक्षा चिंता अथवा तकनीकी पूछताछ हेतु हमारे सुरक्षा डेस्क से संपर्क करें।"
                : "For security disclosures or audit inquiries, contact our dedicated technical desk."}
            </p>
          </div>

          <div className="flex items-center gap-3 shrink-0">
            <a
              href="mailto:pawanbussiness108@gmail.com"
              className="rounded-xl bg-teal-600 px-4 py-2.5 text-xs font-bold text-white hover:bg-teal-500 transition shadow-sm"
            >
              pawanbussiness108@gmail.com
            </a>
          </div>
        </section>
      </main>

      <GovernmentFooter />
    </div>
  );
}
