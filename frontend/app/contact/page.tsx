"use client";

import React from "react";
import Link from "next/link";
import {
  PhoneCall,
  Mail,
  HelpCircle,
  FileCheck2,
  Lock,
  ChevronRight,
} from "lucide-react";
import { GovernmentHeader } from "@/components/shared/GovernmentHeader";
import { GovernmentFooter } from "@/components/shared/GovernmentFooter";
import { useLanguage } from "@/lib/i18n";

export default function ContactPage() {
  const { isHindi } = useLanguage();

  const faqs = [
    {
      q: isHindi ? "आपातकालीन एम्बुलेंस के लिए क्या करें?" : "How do I request an immediate emergency ambulance?",
      a: isHindi
        ? "आपातकालीन एम्बुलेंस सहायता के लिए तत्काल 108 डायल करें। 108 सेवा राज्य आपातकालीन प्रतिक्रिया प्रणाली से सीधे जुड़ी है।"
        : "Dial 108 directly from any mobile or landline across participating States and Union Territories for immediate ambulance dispatch and emergency triage.",
    },
    {
      q: isHindi ? "अस्पताल अपने बेड कैसे ऑनबोर्ड कर सकते हैं?" : "How do hospitals onboard their bed capacity?",
      a: isHindi
        ? "अस्पताल 'अस्पताल पंजीकरण' पेज पर जाकर ऑनलाइन फॉर्म भरें, नोडल अधिकारी ओटीपी सत्यापित करें और आवश्यक दस्तावेज अपलोड करें।"
        : "Healthcare facilities can submit an accreditation dossier via the 'Register Hospital' page, complete Nodal Officer 2FA verification, and upload compliance documents for district review.",
    },
    {
      q: isHindi ? "आवेदन की स्थिति कैसे ट्रैक करें?" : "How do I track my hospital's application status?",
      a: isHindi
        ? "'आवेदन ट्रैक करें' पेज पर जाकर अपना आवेदन क्रमांक (Application Number) और गुप्त ट्रैकिंग टोकन (Secret Token) दर्ज करें।"
        : "Visit the 'Track Application' page and enter your Official Application Number and Secret Tracking Token received via email upon application submission.",
    },
    {
      q: isHindi ? "स्वीकृति के बाद खाता कैसे सक्रिय करें?" : "How do approved facilities activate their credentials?",
      a: isHindi
        ? "अंतिम केंद्रीय अनुमोदन के बाद नोडल अधिकारी को ईमेल द्वारा एक्टिवेशन लिंक भेजा जाता है। लिंक खोलकर सुरक्षित पासवर्ड बनाएं।"
        : "Upon Stage-3 Central Government approval, an official activation email is dispatched containing a one-time link to create a secure password and activate operations.",
    },
  ];

  return (
    <div className="min-h-screen bg-slate-50 text-slate-800 flex flex-col font-sans">
      <GovernmentHeader />

      {/* Page Header */}
      <section className="bg-gradient-to-b from-white to-slate-100 border-b border-slate-200 py-12 sm:py-16">
        <div className="max-w-5xl mx-auto px-4 sm:px-6 text-center space-y-4 animate-fade-in-up">
          <div className="inline-flex items-center gap-2 rounded-full bg-teal-50 border border-teal-200 px-3.5 py-1 text-xs font-bold text-teal-900 tracking-wide">
            <PhoneCall className="w-3.5 h-3.5 text-teal-700" />
            <span>
              {isHindi ? "24/7 सहायता व संपर्क" : "24/7 Support & Assistance"}
            </span>
          </div>

          <h1 className="text-3xl sm:text-4xl font-extrabold text-slate-950 tracking-tight">
            {isHindi ? "संपर्क एवं सहायता केंद्र" : "Contact & Help Center"}
          </h1>

          <p className="text-sm sm:text-base text-slate-600 max-w-2xl mx-auto leading-relaxed">
            {isHindi
              ? "आपातकालीन नंबर, ऑनबोर्डिंग सहायता और तकनीकी मार्गदर्शन हेतु हमारे आधिकारिक सहायता चैनलों से संपर्क करें।"
              : "Access verified national emergency helplines, connect with our hospital accreditation helpdesk, or find answers to common questions."}
          </p>
        </div>
      </section>

      {/* Main Content Body */}
      <main className="flex-1 max-w-6xl mx-auto px-4 sm:px-6 py-12 space-y-12">
        {/* Public Health & Platform Advisory Note */}
        <div className="rounded-2xl border border-teal-200 bg-teal-50/60 p-5 sm:p-6 text-xs text-slate-700 leading-relaxed space-y-2">
          <div className="flex items-center gap-2 font-bold text-teal-900 text-sm">
            <span className="flex h-2.5 w-2.5 rounded-full bg-teal-600" />
            <span>
              {isHindi
                ? "प्लेटफॉर्म उद्देश्य एवं आपातकालीन सूचना परामर्श"
                : "Platform Scope & Emergency Helplines Advisory"}
            </span>
          </div>
          <p>
            {isHindi
              ? "स्वास्थ्य समन्वय (SWASTHYA SAMANVAY) एक डिजिटल अस्पताल समन्वय एवं रेफरल प्लेटफॉर्म है। यह सीधे एम्बुलेंस प्रेषण केंद्र का संचालन नहीं करता है। आपातकालीन एम्बुलेंस (108) एवं राष्ट्रीय स्वास्थ्य हेल्पलाइन (1075) स्वतंत्र सार्वजनिक टेलीफोन सेवाएं हैं जो नागरिकों की सीधी सहायता हेतु कार्यरत हैं।"
              : "SWASTHYA SAMANVAY is a digital hospital resource coordination and patient referral platform; it does not operate a direct ambulance dispatch center. Standard emergency telephone helplines (108 for Ambulance, 1075 for National Health) operate independently as public phone services for direct citizen assistance."}
          </p>
        </div>

        {/* Contact Cards Grid */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {/* Card 1: 108 Ambulance */}
          <div className="rounded-2xl border border-slate-200 bg-white p-6 space-y-4 shadow-xs card-hover-lift">
            <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-emerald-50 text-emerald-700 border border-emerald-200">
              <PhoneCall className="w-6 h-6" />
            </div>
            <div>
              <span className="text-[10px] font-bold uppercase tracking-wider text-emerald-700">
                {isHindi ? "तत्काल आपातकाल" : "Immediate Emergency"}
              </span>
              <h3 className="text-lg font-bold text-slate-900 mt-1">
                {isHindi ? "आपातकालीन एम्बुलेंस: 108" : "Ambulance Emergency: 108"}
              </h3>
            </div>
            <p className="text-xs text-slate-600 leading-relaxed">
              {isHindi
                ? "तीव्र चिकित्सा आपात स्थिति, आघात परिवहन एवं गंभीर रोगी स्थानांतरण हेतु राज्यों एवं केंद्र शासित प्रदेशों में 24/7 टोल-फ्री सेवा।"
                : "Toll-free 24/7 emergency response for acute medical emergencies, trauma transport, and patient critical care dispatch across States and UTs."}
            </p>
            <div className="pt-2 border-t border-slate-100 text-xs font-semibold text-emerald-700">
              {isHindi ? "डायल करें: 108 (24/7 टोल-फ्री)" : "Dial: 108 (24/7 Toll-Free)"}
            </div>
          </div>

          {/* Card 2: 1075 National Helpline */}
          <div className="rounded-2xl border border-slate-200 bg-white p-6 space-y-4 shadow-xs card-hover-lift">
            <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-teal-50 text-teal-700 border border-teal-200">
              <PhoneCall className="w-6 h-6" />
            </div>
            <div>
              <span className="text-[10px] font-bold uppercase tracking-wider text-teal-700">
                {isHindi ? "स्वास्थ्य मार्गदर्शन" : "Public Health Inquiries"}
              </span>
              <h3 className="text-lg font-bold text-slate-900 mt-1">
                {isHindi ? "स्वास्थ्य हेल्पलाइन: 1075" : "Health Helpline: 1075"}
              </h3>
            </div>
            <p className="text-xs text-slate-600 leading-relaxed">
              {isHindi
                ? "चिकित्सकीय मार्गदर्शन, सरकारी स्वास्थ्य योजनाओं, रोग निगरानी और अस्पताल संबंधी जानकारी हेतु राष्ट्रीय स्वास्थ्य सूचना हेल्पलाइन।"
                : "National health information helpline for clinical guidance, government healthcare programs, disease surveillance, and hospital guidance."}
            </p>
            <div className="pt-2 border-t border-slate-100 text-xs font-semibold text-teal-700">
              {isHindi ? "डायल करें: 1075 (24/7 टोल-फ्री)" : "Dial: 1075 (24/7 Toll-Free)"}
            </div>
          </div>

          {/* Card 3: Official Support Desk Email */}
          <div className="rounded-2xl border border-slate-200 bg-white p-6 space-y-4 shadow-xs card-hover-lift">
            <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-indigo-50 text-indigo-700 border border-indigo-200">
              <Mail className="w-6 h-6" />
            </div>
            <div>
              <span className="text-[10px] font-bold uppercase tracking-wider text-indigo-700">
                {isHindi ? "तकनीकी एवं ऑनबोर्डिंग" : "Technical & Onboarding"}
              </span>
              <h3 className="text-lg font-bold text-slate-900 mt-1">
                {isHindi ? "हेल्पडेस्क ईमेल" : "Helpdesk Email"}
              </h3>
            </div>
            <p className="text-xs text-slate-600 leading-relaxed">
              {isHindi
                ? "अस्पताल ऑनबोर्डिंग सहायता, प्रत्यायन पूछताछ, एपीआई एकीकरण अथवा तकनीकी समाधान हेतु हमारे आधिकारिक डेस्क से संपर्क करें।"
                : "For facility onboarding queries, accreditation assistance, API integration questions, or technical support, write to our official desk."}
            </p>
            <div className="pt-2 border-t border-slate-100 text-xs font-semibold">
              <a
                href="mailto:pawanbussiness108@gmail.com"
                className="text-indigo-700 hover:text-indigo-900 underline underline-offset-2 break-all"
              >
                pawanbussiness108@gmail.com
              </a>
            </div>
          </div>
        </div>

        {/* Quick Portal Action Cards */}
        <section className="rounded-2xl bg-[#0B132B] text-white p-8 sm:p-10 space-y-6 shadow-md">
          <div className="space-y-1">
            <span className="text-xs font-bold uppercase tracking-wider text-teal-400">
              {isHindi ? "त्वरित पोर्टल सेवाएं" : "Self-Service Portal Links"}
            </span>
            <h3 className="text-xl sm:text-2xl font-bold text-white">
              {isHindi ? "त्वरित ऑनलाइन सेवाएं" : "Direct Healthcare Actions"}
            </h3>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            <Link
              href="/register/hospital"
              className="p-5 rounded-xl bg-slate-900/90 border border-slate-800 hover:border-teal-500/50 hover:bg-slate-800 transition flex items-center justify-between group"
            >
              <div>
                <h4 className="text-sm font-bold text-white group-hover:text-teal-300">
                  {isHindi ? "अस्पताल पंजीकरण" : "Register Hospital"}
                </h4>
                <p className="text-[11px] text-slate-400 mt-0.5">
                  {isHindi ? "सुविधा प्रत्यायन शुरू करें" : "Begin facility accreditation"}
                </p>
              </div>
              <FileCheck2 className="w-5 h-5 text-teal-400" />
            </Link>

            <Link
              href="/application/status"
              className="p-5 rounded-xl bg-slate-900/90 border border-slate-800 hover:border-indigo-500/50 hover:bg-slate-800 transition flex items-center justify-between group"
            >
              <div>
                <h4 className="text-sm font-bold text-white group-hover:text-indigo-300">
                  {isHindi ? "आवेदन स्थिति" : "Track Application"}
                </h4>
                <p className="text-[11px] text-slate-400 mt-0.5">
                  {isHindi ? "समीक्षा प्रगति जांचें" : "Check review milestones"}
                </p>
              </div>
              <ChevronRight className="w-5 h-5 text-indigo-400" />
            </Link>

            <Link
              href="/activate"
              className="p-5 rounded-xl bg-slate-900/90 border border-slate-800 hover:border-cyan-500/50 hover:bg-slate-800 transition flex items-center justify-between group"
            >
              <div>
                <h4 className="text-sm font-bold text-white group-hover:text-cyan-300">
                  {isHindi ? "खाता सक्रिय करें" : "Activate Account"}
                </h4>
                <p className="text-[11px] text-slate-400 mt-0.5">
                  {isHindi ? "परिचालन पासवर्ड बनाएं" : "Set operational password"}
                </p>
              </div>
              <Lock className="w-5 h-5 text-cyan-400" />
            </Link>
          </div>
        </section>

        {/* Frequently Asked Questions */}
        <section className="space-y-6">
          <div className="space-y-2">
            <span className="text-xs font-bold uppercase tracking-wider text-teal-800 bg-teal-50 border border-teal-200 px-3 py-1 rounded-full">
              {isHindi ? "अक्सर पूछे जाने वाले प्रश्न" : "Frequently Asked Questions"}
            </span>
            <h3 className="text-xl sm:text-2xl font-bold text-slate-900">
              {isHindi ? "सामान्य प्रश्न एवं उत्तर" : "Common Questions & Support"}
            </h3>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {faqs.map((faq, idx) => (
              <div
                key={idx}
                className="rounded-2xl border border-slate-200 bg-white p-6 space-y-2.5 shadow-xs"
              >
                <div className="flex items-start gap-2.5">
                  <HelpCircle className="w-4 h-4 text-teal-700 mt-1 shrink-0" />
                  <h4 className="text-sm font-bold text-slate-900 leading-snug">
                    {faq.q}
                  </h4>
                </div>
                <p className="text-xs text-slate-600 leading-relaxed pl-6.5">
                  {faq.a}
                </p>
              </div>
            ))}
          </div>
        </section>
      </main>

      <GovernmentFooter />
    </div>
  );
}
