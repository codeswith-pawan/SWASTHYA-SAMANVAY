"use client";

import React from "react";
import Link from "next/link";
import {
  BedDouble,
  Activity,
  Ambulance,
  FileCheck2,
  CheckCircle2,
} from "lucide-react";
import { GovernmentHeader } from "@/components/shared/GovernmentHeader";
import { GovernmentFooter } from "@/components/shared/GovernmentFooter";
import { useLanguage } from "@/lib/i18n";

export default function ServicesPage() {
  const { isHindi } = useLanguage();

  const services = [
    {
      id: "bed-tracking",
      title: isHindi ? "रीयल-टाइम बेड एवं आईसीयू ट्रैकिंग" : "Real-Time Bed & ICU Tracking",
      icon: BedDouble,
      iconColor: "text-teal-700 bg-teal-50 border-teal-200",
      description: isHindi
        ? "सभी संबद्ध अस्पतालों में सामान्य, ऑक्सीजन एवं आईसीयू बिस्तरों की अद्यतन उपलब्धता की डिजिटल निगरानी। परमाणु लॉक द्वारा ओवरबुकिंग और कृत्रिम होर्डिंग की रोकथाम।"
        : "Accurate, minute-by-minute tracking of active general beds, oxygen-supported units, and ventilator-equipped ICUs. Backed by atomic row-level reservation locks and automatic 30-minute expiry to ensure capacity is never hoarded.",
      features: isHindi
        ? [
            "विस्तृत बेड श्रेणियां (सामान्य, ऑक्सीजन, आईसीयू, बाल चिकित्सा)",
            "परमाणु पंक्ति-स्तरीय आरक्षण लॉक (शून्य ओवरबुकिंग)",
            "मरीज के न पहुंचने पर 30 मिनट में स्वतः क्षमता अवमुक्ति",
            "वास्तविक समय इन्वेंट्री समायोजन हेतु अस्पताल डैशबोर्ड",
          ]
        : [
            "Granular bed categories (General, Oxygen, ICU, Pediatric)",
            "Atomic row-level reservation locks with zero overbooking",
            "Automatic 30-minute expiry release on unconfirmed patient arrival",
            "Facility-level dashboard for real-time inventory adjustments",
          ],
    },
    {
      id: "smart-referral",
      title: isHindi ? "स्थिति-आधारित क्लिनिकल रेफरल" : "Condition-Based Patient Referral",
      icon: Activity,
      iconColor: "text-indigo-700 bg-indigo-50 border-indigo-200",
      description: isHindi
        ? "मरीज की महत्वपूर्ण जीवन संकेत (GCS, SpO2, रक्तचाप, आदि), विशिष्ट चिकित्सा आवश्यकता और निकटता के आधार पर सक्षम गंतव्य अस्पताल का त्वरित चयन।"
        : "Intelligent clinical decision support evaluating patient vitals (GCS, SpO2, MAP, lactate) and medical specialty requirements against destination hospital capabilities and Haversine distance ranking.",
      features: isHindi
        ? [
            "महत्वपूर्ण शारीरिक संकेतों पर आधारित वास्तविक समय ट्रायज स्कोरिंग",
            "चिकित्सा विशेषज्ञता मिलान (हृदय रोग, ट्रॉमा, न्यूरो, बर्न)",
            "त्वरित एम्बुलेंस पारगमन हेतु हैवर्सिन निकटता दूरी रैंकिंग",
            "संरचित रेफरल जीवन-चक्र (लंबित से पूर्ण तक)",
          ]
        : [
            "Real-time triage scoring based on vital physiological signs",
            "Specialty capability matching (Cardiology, Trauma, Neuro, Burn)",
            "Haversine proximity distance ranking for rapid ambulance transit",
            "Structured referral lifecycle state machine (Pending to Complete)",
          ],
    },
    {
      id: "ambulance-coordination",
      title: isHindi ? "एम्बुलेंस प्रेषण एवं पारगमन समन्वय" : "Ambulance Dispatch & Transit Coordination",
      icon: Ambulance,
      iconColor: "text-emerald-700 bg-emerald-50 border-emerald-200",
      description: isHindi
        ? "रेफरल स्वीकृत होने पर गंतव्य अस्पताल को तत्काल सूचना एवं मरीज के आगमन से पूर्व आईसीयू टीम की तैयारी सुनिश्चित करना।"
        : "End-to-end operational coordination between referring and destination medical centers. The destination facility receives complete patient history and reserves the bed before the ambulance arrives.",
      features: isHindi
        ? [
            "प्रेषण होते ही गंतव्य अस्पताल को तत्काल डिजिटल अलर्ट",
            "108 आपातकालीन एम्बुलेंस नेटवर्क के साथ सीधा समन्वय",
            "मरीज के आगमन पूर्व आपातकालीन कक्ष और आईसीयू टीम की तत्परता",
            "बेडसाइड प्रवेश पुष्टि एवं मरीज सुपुर्दगी ट्रैकिंग",
          ]
        : [
            "Immediate destination facility notification upon dispatch",
            "Direct coordination with 108 Emergency Ambulance Network",
            "Pre-arrival emergency room and critical care team alerts",
            "Bedside admission confirmation and patient handoff tracking",
          ],
    },
    {
      id: "accreditation",
      title: isHindi ? "डिजिटल अस्पताल प्रत्यायन एवं सत्यापन" : "Digital Hospital Accreditation & Onboarding",
      icon: FileCheck2,
      iconColor: "text-purple-700 bg-purple-50 border-purple-200",
      description: isHindi
        ? "स्वास्थ्य संस्थानों का पारदर्शी चार-चरणीय ऑनबोर्डिंग, नोडल अधिकारी 2FA सत्यापन एवं विनियामक प्रमाण-पत्रों का डिजिटल ऑडिट।"
        : "A transparent 4-stage regulatory workflow requiring Nodal Officer 2FA verification, clinical establishment certification, fire NOC, and bio-medical waste clearances before gaining network admission.",
      features: isHindi
        ? [
            "भौगोलिक निर्देशांक कैप्चर के साथ ऑनलाइन स्व-पंजीकरण",
            "नोडल अधिकारी 2FA प्रमाणीकरण (सुरक्षित ओटीपी सत्यापन)",
            "दस्तावेज़ अनुपालन ऑडिट (क्लिनिकल प्रतिष्ठान, फायर एनओसी)",
            "जिला, राज्य एवं केंद्र द्वारा बहु-स्तरीय विनियामक अनुमोदन",
          ]
        : [
            "Online self-registration with geo-coordinate capture",
            "Nodal Officer two-factor authentication (OTP verification)",
            "Document compliance audit (Clinical establishment, Fire NOC)",
            "Multi-tier regulatory approval by District, State, and Central reviewers",
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
            <Activity className="w-3.5 h-3.5 text-teal-700" />
            <span>
              {isHindi ? "मुख्य सेवाएं एवं सुविधाएं" : "Core Platform Capabilities"}
            </span>
          </div>

          <h1 className="text-3xl sm:text-4xl font-extrabold text-slate-950 tracking-tight">
            {isHindi ? "आरोग्यसेतु ग्रिड की सेवाएं" : "Healthcare System Services"}
          </h1>

          <p className="text-sm sm:text-base text-slate-600 max-w-3xl mx-auto leading-relaxed">
            {isHindi
              ? "स्वास्थ्य प्रशासकों, आपातकालीन डॉक्टरों और मरीजों के लिए विश्वसनीय, सुरक्षित और त्वरित डिजिटल समाधान।"
              : "Mission-critical operational capabilities engineered to maintain bed availability, streamline emergency patient dispatch, and uphold regulatory accountability across participating healthcare institutions."}
          </p>
        </div>
      </section>

      {/* Main Services List */}
      <main className="flex-1 max-w-6xl mx-auto px-4 sm:px-6 py-12 space-y-12">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
          {services.map((svc) => {
            const Icon = svc.icon;
            return (
              <div
                key={svc.id}
                className="rounded-2xl border border-slate-200 bg-white p-7 space-y-5 shadow-xs hover:border-teal-300 hover:shadow-md transition flex flex-col justify-between card-hover-lift"
              >
                <div className="space-y-4">
                  <div className="flex items-center gap-3">
                    <div
                      className={`flex h-12 w-12 items-center justify-center rounded-xl border ${svc.iconColor} shadow-xs shrink-0`}
                    >
                      <Icon className="w-6 h-6" />
                    </div>
                    <h2 className="text-lg font-bold text-slate-900 leading-snug">
                      {svc.title}
                    </h2>
                  </div>

                  <p className="text-xs sm:text-sm text-slate-600 leading-relaxed">
                    {svc.description}
                  </p>

                  <div className="pt-3 border-t border-slate-100 space-y-2">
                    <span className="text-[11px] font-bold uppercase tracking-wider text-slate-400">
                      {isHindi ? "मुख्य विशेषताएं:" : "Key Highlights:"}
                    </span>
                    <ul className="space-y-1.5 text-xs text-slate-700">
                      {svc.features.map((feat, idx) => (
                        <li key={idx} className="flex items-start gap-2">
                          <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600 mt-0.5 shrink-0" />
                          <span>{feat}</span>
                        </li>
                      ))}
                    </ul>
                  </div>
                </div>
              </div>
            );
          })}
        </div>

        {/* Quick Help Strip */}
        <section className="rounded-2xl border border-slate-200 bg-white p-6 sm:p-8 flex flex-col sm:flex-row items-center justify-between gap-6 shadow-xs">
          <div className="space-y-1 text-center sm:text-left">
            <h3 className="text-base font-bold text-slate-900">
              {isHindi ? "अस्पताल ऑनबोर्डिंग अथवा आवेदन ट्रैकिंग" : "Ready to Onboard or Track Your Facility?"}
            </h3>
            <p className="text-xs text-slate-500">
              {isHindi
                ? "नया अस्पताल पंजीकृत करें या मौजूदा आवेदन की वर्तमान स्थिति जांचें।"
                : "Submit fresh institutional credentials or monitor review progress through our public portal."}
            </p>
          </div>

          <div className="flex items-center gap-3 shrink-0">
            <Link
              href="/register/hospital"
              className="rounded-xl bg-teal-700 px-5 py-2.5 text-xs font-bold text-white hover:bg-teal-800 transition shadow-xs"
            >
              {isHindi ? "अस्पताल पंजीकरण" : "Register Facility"}
            </Link>
            <Link
              href="/application/status"
              className="rounded-xl border border-slate-300 bg-slate-50 px-4 py-2.5 text-xs font-semibold text-slate-700 hover:bg-slate-100 transition"
            >
              {isHindi ? "आवेदन स्थिति" : "Track Status"}
            </Link>
          </div>
        </section>
      </main>

      <GovernmentFooter />
    </div>
  );
}
