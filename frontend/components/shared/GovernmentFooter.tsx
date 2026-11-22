"use client";

import React from "react";
import Link from "next/link";
import { Hospital, ShieldCheck, Mail, Phone, Lock, Activity } from "lucide-react";
import { useLanguage } from "@/lib/i18n";

export const GovernmentFooter: React.FC = () => {
  const { isHindi } = useLanguage();

  return (
    <footer className="bg-[#0B132B] text-slate-300 border-t border-slate-800 text-xs font-sans">
      {/* 24/7 Emergency Helpline Strip */}
      <div className="bg-[#070D1E] border-b border-slate-800/80 py-3 px-4 sm:px-6">
        <div className="max-w-7xl mx-auto flex flex-col sm:flex-row items-center justify-between gap-3 text-xs">
          <div className="flex items-center gap-2 text-teal-400 font-semibold tracking-wide">
            <span className="flex h-2 w-2 rounded-full bg-emerald-400 animate-pulse-glow" />
            <span>
              {isHindi
                ? "24/7 राष्ट्रीय आपातकालीन एवं क्रिटिकल केयर टेलीमेट्री नेटवर्क"
                : "24/7 National Emergency & Critical Care Telemetry Network"}
            </span>
          </div>

          <div className="flex flex-wrap items-center gap-4 text-slate-300">
            <div className="flex items-center gap-1.5">
              <Phone className="w-3.5 h-3.5 text-teal-400" />
              <span>
                {isHindi ? "आपातकालीन एम्बुलेंस:" : "Ambulance Emergency:"}{" "}
                <strong className="text-white">108</strong>{" "}
                <span className="text-slate-400">
                  {isHindi ? "(राज्य व केंद्र शासित प्रदेश)" : "(States & UTs)"}
                </span>
              </span>
            </div>
            <span className="text-slate-600 hidden sm:inline">•</span>
            <div className="flex items-center gap-1.5">
              <Phone className="w-3.5 h-3.5 text-emerald-400" />
              <span>
                {isHindi ? "स्वास्थ्य हेल्पलाइन:" : "Health Helpline:"}{" "}
                <strong className="text-white">1075</strong>{" "}
                <span className="text-slate-400">
                  {isHindi ? "(टोल-फ्री)" : "(Toll-Free)"}
                </span>
              </span>
            </div>
            <span className="text-slate-600 hidden sm:inline">•</span>
            <div className="flex items-center gap-1.5">
              <Mail className="w-3.5 h-3.5 text-slate-400" />
              <a
                href="mailto:pawanbussiness108@gmail.com"
                className="text-teal-300 hover:text-white underline underline-offset-2"
              >
                pawanbussiness108@gmail.com
              </a>
            </div>
          </div>
        </div>
      </div>

      {/* Main Footer Links */}
      <div className="max-w-7xl mx-auto px-4 sm:px-6 py-12">
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-8">
          {/* Col 1 & 2: Brand Identity & Infrastructure Description */}
          <div className="lg:col-span-2 space-y-4">
            <div className="flex items-center gap-3">
              <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-teal-950/80 border border-teal-500/30 text-white">
                <Hospital className="w-5 h-5 text-teal-400" />
              </div>
              <div>
                <span className="text-base font-bold text-white tracking-tight">
                  ArogyaSetu Grid
                </span>
                <p className="text-[11px] text-teal-300/80 font-medium">
                  {isHindi
                    ? "अस्पताल समन्वय एवं रेफरल पोर्टल"
                    : "Hospital Coordination & Referral Portal"}
                </p>
              </div>
            </div>

            <p className="text-xs text-slate-400 leading-relaxed pr-4">
              {isHindi
                ? "शून्य-विलंब आपातकालीन रेफरल, वास्तविक समय बेड आरक्षण और बहु-स्तरीय सुविधा प्रत्यायन हेतु अग्रणी अस्पतालों, जिला स्वास्थ्य प्रशासनों और राज्य स्वास्थ्य निदेशालयों को जोड़ने वाली एकीकृत डिजिटल स्वास्थ्य अवसंरचना।"
                : "A unified digital healthcare infrastructure connecting frontline hospitals, district health administrations, and state health directorates for zero-delay emergency referrals, atomic bed reservation, and multi-tier facility accreditation."}
            </p>

            <div className="flex flex-col sm:flex-row items-start sm:items-center gap-3 pt-2 text-[11px] text-slate-400">
              <div className="flex items-center gap-1.5 text-emerald-400 font-medium">
                <ShieldCheck className="w-4 h-4 shrink-0" />
                <span>
                  {isHindi ? "सख्त क्षेत्राधिकार डेटा पृथक्करण" : "Strict Jurisdictional Data Isolation"}
                </span>
              </div>
              <span className="text-slate-600 hidden sm:inline">•</span>
              <div className="flex items-center gap-1.5 text-teal-300 font-medium">
                <Lock className="w-3.5 h-3.5 shrink-0" />
                <span>
                  {isHindi ? "नोडल अधिकारी 2FA प्रमाणीकृत" : "Nodal Officer 2FA Authenticated"}
                </span>
              </div>
            </div>
          </div>

          {/* Col 3: Department Portals */}
          <div>
            <h4 className="text-xs font-bold text-white uppercase tracking-wider mb-3">
              {isHindi ? "विभागीय पोर्टल" : "Department Portals"}
            </h4>
            <ul className="space-y-2 text-xs">
              <li>
                <Link
                  href="/portal/hospital/login"
                  className="text-slate-300 hover:text-white hover:underline transition"
                >
                  {isHindi ? "अस्पताल संचालन पोर्टल" : "Hospital Operations Portal"}
                </Link>
              </li>
              <li>
                <Link
                  href="/portal/district/login"
                  className="text-slate-300 hover:text-white hover:underline transition"
                >
                  {isHindi ? "जिला स्वास्थ्य प्राधिकरण" : "District Health Authority"}
                </Link>
              </li>
              <li>
                <Link
                  href="/portal/state/login"
                  className="text-slate-300 hover:text-white hover:underline transition"
                >
                  {isHindi ? "राज्य स्वास्थ्य निदेशालय" : "State Health Directorate"}
                </Link>
              </li>
              <li>
                <Link
                  href="/portal/central/login"
                  className="text-slate-300 hover:text-white hover:underline transition"
                >
                  {isHindi ? "केंद्रीय स्वास्थ्य कमान" : "Central Health Command"}
                </Link>
              </li>
              <li>
                <Link
                  href="/portal"
                  className="text-teal-400 hover:text-teal-300 font-semibold inline-flex items-center gap-1"
                >
                  <span>{isHindi ? "सभी पोर्टल विवरण" : "All Portals Overview"}</span>
                  <span>→</span>
                </Link>
              </li>
            </ul>
          </div>

          {/* Col 4: Accreditation & Tracking */}
          <div>
            <h4 className="text-xs font-bold text-white uppercase tracking-wider mb-3">
              {isHindi ? "प्रत्यायन एवं ट्रैकिंग" : "Accreditation & Tracking"}
            </h4>
            <ul className="space-y-2 text-xs">
              <li>
                <Link
                  href="/register/hospital"
                  className="text-slate-300 hover:text-white hover:underline transition"
                >
                  {isHindi ? "अस्पताल सुविधा पंजीकरण" : "Hospital Facility Onboarding"}
                </Link>
              </li>
              <li>
                <Link
                  href="/register/district"
                  className="text-slate-300 hover:text-white hover:underline transition"
                >
                  {isHindi ? "जिला प्राधिकरण पंजीकरण" : "District Authority Registration"}
                </Link>
              </li>
              <li>
                <Link
                  href="/register/state"
                  className="text-slate-300 hover:text-white hover:underline transition"
                >
                  {isHindi ? "राज्य निदेशालय पंजीकरण" : "State Directorate Registration"}
                </Link>
              </li>
              <li>
                <Link
                  href="/application/status"
                  className="text-slate-300 hover:text-white hover:underline transition"
                >
                  {isHindi ? "आवेदन स्थिति ट्रैक करें" : "Track Application Status"}
                </Link>
              </li>
              <li>
                <Link
                  href="/activate"
                  className="text-slate-300 hover:text-white hover:underline transition"
                >
                  {isHindi ? "स्वीकृत खाता सक्रिय करें" : "Activate Provisioned Account"}
                </Link>
              </li>
            </ul>
          </div>

          {/* Col 5: Security & Technical Contact */}
          <div>
            <h4 className="text-xs font-bold text-white uppercase tracking-wider mb-3">
              {isHindi ? "तकनीकी सहायता" : "Technical Inquiries"}
            </h4>
            <ul className="space-y-2.5 text-xs text-slate-400">
              <li className="flex items-start gap-2">
                <Mail className="w-3.5 h-3.5 text-teal-400 shrink-0 mt-0.5" />
                <span>
                  {isHindi ? "सहायता केंद्र:" : "Support Desk:"}{" "}
                  <a
                    href="mailto:pawanbussiness108@gmail.com"
                    className="text-white hover:underline font-medium"
                  >
                    pawanbussiness108@gmail.com
                  </a>
                </span>
              </li>
              <li className="flex items-start gap-2">
                <Activity className="w-3.5 h-3.5 text-emerald-400 shrink-0 mt-0.5" />
                <span>
                  {isHindi
                    ? "एपीआई एवं टेलीमेट्री: सक्रिय (99.98% SLA)"
                    : "API & Telemetry Health: Operational (99.98% SLA)"}
                </span>
              </li>
              <li className="pt-2 text-[11px] text-slate-400 leading-relaxed border-t border-slate-800">
                {isHindi
                  ? "आधिकारिक क्रिटिकल केयर समन्वय एवं आपातकालीन स्वास्थ्य प्रणाली। केवल अधिकृत स्वास्थ्य कर्मियों के उपयोग हेतु।"
                  : "Official critical care coordination and emergency health logistics system. Authorized healthcare personnel access only."}
              </li>
            </ul>
          </div>
        </div>
      </div>

      {/* Emerald Divider */}
      <div className="h-px w-full bg-gradient-to-r from-teal-500/10 via-teal-500/40 to-cyan-500/10" />

      {/* Bottom Copyright & Compliance Bar */}
      <div className="bg-[#070D1E] py-4 px-4 sm:px-6 text-[11px] text-slate-400">
        <div className="max-w-7xl mx-auto flex flex-col sm:flex-row items-center justify-between gap-3">
          <div>
            <p>
              {isHindi
                ? "© 2026 ArogyaSetu Grid। राष्ट्रीय क्रिटिकल केयर एवं अस्पताल कमान नेटवर्क। सर्वाधिकार सुरक्षित।"
                : "© 2026 ArogyaSetu Grid. National Critical Care & Hospital Command Network. All rights reserved."}
            </p>
            <p className="text-[10px] text-slate-500 mt-0.5">
              Smart India Hackathon Technical Prototype &bull; Developed for technological demonstration; not an official Government of India portal.
            </p>
          </div>
          <div className="flex flex-wrap items-center gap-4 text-slate-400">
            <Link
              href="/policies/security"
              className="hover:text-slate-200 transition underline-offset-2 hover:underline"
            >
              {isHindi ? "सुरक्षा नीति" : "Security Policy"}
            </Link>
            <span>•</span>
            <Link
              href="/policies/terms"
              className="hover:text-slate-200 transition underline-offset-2 hover:underline"
            >
              {isHindi ? "सेवा की शर्तें" : "Terms of Service"}
            </Link>
            <span>•</span>
            <Link
              href="/policies/governance"
              className="hover:text-slate-200 transition underline-offset-2 hover:underline"
            >
              {isHindi ? "क्षेत्राधिकार शासन" : "Jurisdictional Governance"}
            </Link>
            <span>•</span>
            <Link
              href="/policies/sla"
              className="hover:text-slate-200 transition underline-offset-2 hover:underline"
            >
              {isHindi ? "अस्पताल सेवा मानक (SLA)" : "Inter-Hospital SLAs"}
            </Link>
          </div>
        </div>
      </div>
    </footer>
  );
};
