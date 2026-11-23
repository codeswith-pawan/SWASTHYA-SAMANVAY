"use client";

import React from "react";
import Link from "next/link";
import {
  Hospital,
  Building2,
  ShieldCheck,
  Globe,
  FileCheck2,
  CheckCircle2,
} from "lucide-react";
import { GovernmentHeader } from "@/components/shared/GovernmentHeader";
import { GovernmentFooter } from "@/components/shared/GovernmentFooter";
import { useLanguage } from "@/lib/i18n";

export default function NetworkPage() {
  const { isHindi } = useLanguage();

  const tiers = [
    {
      level: isHindi ? "स्तर 1 • प्राथमिक देखभाल" : "Tier 1 • Primary Level",
      name: isHindi ? "सामुदायिक स्वास्थ्य केंद्र (CHCs / PHCs)" : "Community & Primary Health Centers",
      badgeColor: "bg-blue-100 text-blue-900 border-blue-200",
      icon: Hospital,
      iconColor: "text-blue-700 bg-blue-50 border-blue-200",
      description: isHindi
        ? "ग्रामीण व उप-मंडलीय स्तर पर प्राथमिक क्लिनिकल ट्रायज, आपातकालीन स्थिरीकरण, सामान्य बेड इनटेक एवं क्षेत्रीय नेटवर्क में रेफरल की शुरुआत।"
        : "Initial emergency stabilization, basic clinical triage, maternity care, and frontline patient referral into the district-wide hospital network.",
      capabilities: isHindi
        ? [
            "प्रथम संपर्क आपातकालीन ट्रायज एवं स्थिरीकरण",
            "सामान्य इनपेशेंट अवलोकन बेड",
            "बुनियादी नैदानिक परीक्षण एवं जीवन संकेत टेलीमेट्री",
            "क्षेत्रीय नेटवर्क में सीधा रेफरल आरंभ करना",
          ]
        : [
            "First-contact emergency triage & stabilization",
            "General inpatient observation beds",
            "Basic diagnostic testing and vital telemetry",
            "Direct referral initiation into regional network",
          ],
    },
    {
      level: isHindi ? "स्तर 2 • द्वितीयक देखभाल" : "Tier 2 • Secondary Level",
      name: isHindi ? "जिला सामान्य एवं उप-मंडलीय अस्पताल" : "District General & Sub-Divisional Hospitals",
      badgeColor: "bg-indigo-100 text-indigo-900 border-indigo-200",
      icon: Building2,
      iconColor: "text-indigo-700 bg-indigo-50 border-indigo-200",
      description: isHindi
        ? "माध्यमिक तीव्र चिकित्सा, आपातकालीन सर्जरी, इंटरमीडिएट आईसीयू, ऑक्सीजन आपूर्ति एवं जिला-स्तरीय एम्बुलेंस इनटेक।"
        : "Secondary acute care, surgical operations, oxygen-supported beds, intermediate ICUs, and district-wide ambulance coordination.",
      capabilities: isHindi
        ? [
            "व्यापक ट्रॉमा एवं सामान्य आपातकालीन सर्जरी",
            "ऑक्सीजन-समर्थित एवं इंटरमीडिएट आईसीयू वार्ड",
            "रक्त भंडारण एवं 24/7 नैदानिक रेडियोलॉजी",
            "जिला-स्तरीय मरीज इनटेक एवं क्रॉस-रेफरल",
          ]
        : [
            "Comprehensive trauma and general surgeries",
            "Oxygen-supported and intermediate ICU wards",
            "Blood storage and 24/7 diagnostic radiology",
            "District-level patient intake and cross-referral",
          ],
    },
    {
      level: isHindi ? "स्तर 3 • तृतीयक देखभाल" : "Tier 3 • Tertiary Level",
      name: isHindi ? "मेडिकल कॉलेज एवं तृतीयक संस्थान" : "Medical Colleges & Tertiary Centers",
      badgeColor: "bg-teal-100 text-teal-900 border-teal-200",
      icon: ShieldCheck,
      iconColor: "text-teal-700 bg-teal-50 border-teal-200",
      description: isHindi
        ? "मल्टी-स्पेशियलिटी क्रिटिकल केयर, उन्नत मैकेनिकल वेंटिलेटर, समर्पित लेवल-1 ट्रॉमा सेंटर एवं अंतर-जिला मरीज रेफरल।"
        : "Multi-specialty critical care, advanced mechanical ventilator management, dedicated trauma care units, and inter-district patient transfers.",
      capabilities: isHindi
        ? [
            "उन्नत गहन चिकित्सा इकाइयां (मेडिकल/सर्जिकल आईसीयू)",
            "विशेष नैदानिक विभाग (कार्डियोलॉजी, न्यूरो, नेफ्रो)",
            "24/7 तत्परता के साथ समर्पित लेवल-1 ट्रॉमा सेंटर",
            "आपातकालीन स्थानांतरण हेतु स्वचालित बेड आरक्षण",
          ]
        : [
            "Advanced intensive care units (Medical/Surgical ICUs)",
            "Specialized clinical departments (Cardiology, Neuro, Nephro)",
            "Dedicated Level-1 trauma centers with 24/7 readiness",
            "Automated bed reservations for incoming emergency transfers",
          ],
    },
    {
      level: isHindi ? "स्तर 4 • शीर्ष विशिष्टता" : "Tier 4 • Apex Level",
      name: isHindi ? "राष्ट्रीय शीर्ष विशिष्टता संस्थान (Apex Institutes)" : "Apex Specialty Institutes & AIIMS",
      badgeColor: "bg-purple-100 text-purple-900 border-purple-200",
      icon: Globe,
      iconColor: "text-purple-700 bg-purple-50 border-purple-200",
      description: isHindi
        ? "राष्ट्रीय शीर्ष संस्थान (जैसे AIIMS, राज्य सुपर-स्पेशियलिटी केंद्र) जिनमें उच्च-निर्भरता आईसीयू, सुपर-स्पेशियलिटी इनटेक और केंद्रीय स्वास्थ्य निगरानी उपलब्ध है।"
        : "Premier national institutions providing super-specialty intensive care, organ-specific interventions, state/national transfer reception, and centralized health surge logistics.",
      capabilities: isHindi
        ? [
            "सुपर-स्पेशियलिटी देखभाल एवं जटिल तृतीयक हस्तक्षेप",
            "उच्च-निर्भरता गहन चिकित्सा एवं उन्नत ईसीएमओ/जीवन रक्षक प्रणाली",
            "राज्य एवं राष्ट्रीय स्तर पर मरीज इनटेक समन्वय",
            "शीर्ष नीति एवं संसाधन सर्ज कमान में भागीदारी",
          ]
        : [
            "Super-specialty care and complex tertiary interventions",
            "High-dependency intensive care & advanced ECMO/life support",
            "State and national level patient intake coordination",
            "Apex policy and resource surge command participation",
          ],
    },
  ];

  return (
    <div className="min-h-screen bg-slate-50 text-slate-800 flex flex-col font-sans">
      <GovernmentHeader />

      {/* Page Header */}
      <section className="bg-gradient-to-b from-white to-slate-100 border-b border-slate-200 py-12 sm:py-16">
        <div className="max-w-5xl mx-auto px-4 sm:px-6 text-center space-y-4 animate-fade-in-up">
          <div className="inline-flex items-center gap-2 rounded-full bg-teal-50 border border-teal-200 px-3.5 py-1 text-xs font-bold text-teal-900 tracking-wide">
            <Hospital className="w-3.5 h-3.5 text-teal-700" />
            <span>
              {isHindi ? "राष्ट्रीय अस्पताल संजाल" : "National Healthcare Network"}
            </span>
          </div>

          <h1 className="text-3xl sm:text-4xl font-extrabold text-slate-950 tracking-tight">
            {isHindi ? "संबद्ध अस्पताल नेटवर्क" : "Hospital Network Architecture"}
          </h1>

          <p className="text-sm sm:text-base text-slate-600 max-w-3xl mx-auto leading-relaxed">
            {isHindi
              ? "प्राथमिक सामुदायिक स्वास्थ्य केंद्रों से लेकर शीर्ष राष्ट्रीय चिकित्सा संस्थानों तक 4-स्तरीय समन्वित स्वास्थ्य अवसंरचना।"
              : "A structured, accredited four-tier healthcare delivery hierarchy ensuring every patient is seamlessly escalated to the nearest appropriate medical facility without delays or bed hoarding."}
          </p>

          <div className="pt-2">
            <Link
              href="/register/hospital"
              className="inline-flex items-center gap-2 rounded-xl bg-teal-700 px-5 py-3 text-xs font-bold text-white hover:bg-teal-800 transition shadow-xs"
            >
              <FileCheck2 className="w-4 h-4" />
              <span>{isHindi ? "अस्पताल को नेटवर्क में जोड़ें" : "Join the Hospital Network"}</span>
            </Link>
          </div>
        </div>
      </section>

      {/* 4-Tier Continuum Cards */}
      <main className="flex-1 max-w-6xl mx-auto px-4 sm:px-6 py-12 space-y-12">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
          {tiers.map((tier, idx) => {
            const Icon = tier.icon;
            return (
              <div
                key={idx}
                className="rounded-2xl border border-slate-200 bg-white p-7 space-y-4 shadow-xs hover:border-teal-300 hover:shadow-md transition flex flex-col justify-between card-hover-lift"
              >
                <div className="space-y-4">
                  <div className="flex items-center justify-between">
                    <span
                      className={`rounded-full px-3 py-1 text-[10px] font-bold uppercase tracking-wider border ${tier.badgeColor}`}
                    >
                      {tier.level}
                    </span>
                    <div
                      className={`flex h-10 w-10 items-center justify-center rounded-xl border ${tier.iconColor}`}
                    >
                      <Icon className="w-5 h-5" />
                    </div>
                  </div>

                  <h2 className="text-lg font-bold text-slate-900 leading-snug">
                    {tier.name}
                  </h2>

                  <p className="text-xs sm:text-sm text-slate-600 leading-relaxed">
                    {tier.description}
                  </p>

                  <div className="pt-3 border-t border-slate-100 space-y-2">
                    <span className="text-[11px] font-bold uppercase tracking-wider text-slate-400">
                      {isHindi ? "स्तर क्षमताएं:" : "Tier Capabilities:"}
                    </span>
                    <ul className="space-y-1.5 text-xs text-slate-700">
                      {tier.capabilities.map((cap, cidx) => (
                        <li key={cidx} className="flex items-start gap-2">
                          <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600 mt-0.5 shrink-0" />
                          <span>{cap}</span>
                        </li>
                      ))}
                    </ul>
                  </div>
                </div>
              </div>
            );
          })}
        </div>

        {/* How Hospitals Join the Network */}
        <section className="rounded-2xl border border-slate-200 bg-white p-8 sm:p-10 space-y-6 shadow-xs">
          <div className="max-w-3xl space-y-2">
            <span className="text-xs font-bold uppercase tracking-wider text-teal-800 bg-teal-50 border border-teal-200 px-3 py-1 rounded-full">
              {isHindi ? "प्रत्यायन मानक" : "Network Admission Process"}
            </span>
            <h3 className="text-xl sm:text-2xl font-bold text-slate-900">
              {isHindi ? "अस्पताल नेटवर्क में कैसे शामिल हों?" : "How Healthcare Facilities Join Swasthya Samanvay"}
            </h3>
            <p className="text-xs sm:text-sm text-slate-600 leading-relaxed">
              {isHindi
                ? "प्रत्येक स्वास्थ्य संस्थान को लाइव बेड बुकिंग की सुविधा प्राप्त करने से पूर्व क्लिनिकल अनुपालन, अग्नि सुरक्षा और नोडल अधिकारी जवाबदेही सुनिश्चित करने हेतु एक संरचित डिजिटल प्रत्यायन प्रक्रिया से गुजरना होता है।"
                : "Every healthcare institution undergoes a structured digital accreditation pipeline to guarantee clinical compliance, fire safety, and nodal officer accountability before gaining access to live bed booking."}
            </p>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 text-xs">
            <div className="p-4 rounded-xl bg-slate-50 border border-slate-200 space-y-1.5">
              <span className="font-bold text-teal-800">
                {isHindi ? "1. सुविधा विवरण" : "1. Facility Profile"}
              </span>
              <p className="text-slate-600 text-[11px]">
                {isHindi
                  ? "बेड संख्या, ऑक्सीजन अवसंरचना, वेंटिलेटर एवं भौगोलिक निर्देशांक दर्ज करें।"
                  : "Submit bed count, oxygen infrastructure, ventilators, and geo-coordinates."}
              </p>
            </div>
            <div className="p-4 rounded-xl bg-slate-50 border border-slate-200 space-y-1.5">
              <span className="font-bold text-indigo-800">
                {isHindi ? "2. नोडल अधिकारी 2FA" : "2. Nodal Officer 2FA"}
              </span>
              <p className="text-slate-600 text-[11px]">
                {isHindi
                  ? "प्राधिकार की पुष्टि हेतु आधिकारिक ईमेल पर सुरक्षित दो-चरणीय सत्यापन।"
                  : "Two-factor verification via official institutional email to verify authority."}
              </p>
            </div>
            <div className="p-4 rounded-xl bg-slate-50 border border-slate-200 space-y-1.5">
              <span className="font-bold text-emerald-800">
                {isHindi ? "3. दस्तावेज़ ऑडिट" : "3. Document Audit"}
              </span>
              <p className="text-slate-600 text-[11px]">
                {isHindi
                  ? "क्लिनिकल एस्टेब्लिशमेंट एक्ट प्रमाणपत्र, फायर एनओसी व कचरा प्रबंधन क्लीयरेंस अपलोड करें।"
                  : "Upload Clinical Establishment Act certificate, Fire NOC, and waste management clearance."}
              </p>
            </div>
            <div className="p-4 rounded-xl bg-slate-50 border border-slate-200 space-y-1.5">
              <span className="font-bold text-purple-800">
                {isHindi ? "4. विनियामक अनुमोदन" : "4. Regulatory Approval"}
              </span>
              <p className="text-slate-600 text-[11px]">
                {isHindi
                  ? "जिला, राज्य व केंद्रीय प्राधिकारियों द्वारा क्रमिक समीक्षा व खाता सक्रियण।"
                  : "Sequential review by District, State, and Central authorities followed by account activation."}
              </p>
            </div>
          </div>

          <div className="pt-2 flex flex-wrap items-center gap-3">
            <Link
              href="/register/hospital"
              className="rounded-xl bg-teal-700 px-5 py-2.5 text-xs font-bold text-white hover:bg-teal-800 transition shadow-xs"
            >
              {isHindi ? "अस्पताल प्रत्यायन शुरू करें →" : "Start Facility Accreditation →"}
            </Link>
            <Link
              href="/application/status"
              className="rounded-xl border border-slate-300 bg-white px-4 py-2.5 text-xs font-semibold text-slate-700 hover:bg-slate-50 transition"
            >
              {isHindi ? "आवेदन स्थिति जांचें" : "Track Existing Application"}
            </Link>
          </div>
        </section>
      </main>

      <GovernmentFooter />
    </div>
  );
}
