"use client";

import React, { useState } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import {
  Menu,
  X,
  PhoneCall,
  LogIn,
  FileCheck2,
  Hospital,
  ChevronRight,
  Shield,
} from "lucide-react";
import { getStoredUser, clearStoredSession } from "@/lib/api";
import { User } from "@/lib/types";
import { useLanguage } from "@/lib/i18n";

export interface GovernmentHeaderProps {
  language?: "en" | "hi";
  onLanguageChange?: (lang: "en" | "hi") => void;
}

export const GovernmentHeader: React.FC<GovernmentHeaderProps> = ({
  language,
  onLanguageChange,
}) => {
  const pathname = usePathname();
  const router = useRouter();
  const { lang: contextLang, setLang: setContextLang } = useLanguage();
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const [user, setUser] = useState<User | null>(() => getStoredUser());

  const currentLang = language || contextLang;
  const isHindi = currentLang === "hi";

  const handleLangToggle = (targetLang: "en" | "hi") => {
    setContextLang(targetLang);
    if (onLanguageChange) {
      onLanguageChange(targetLang);
    }
  };

  const handleSignOut = () => {
    clearStoredSession();
    setUser(null);
    router.push("/portal");
  };

  const navLinks = [
    { href: "/", label: isHindi ? "होम" : "Home" },
    { href: "/about", label: isHindi ? "हमारे बारे में" : "About Us" },
    { href: "/services", label: isHindi ? "सेवाएं" : "Services" },
    { href: "/network", label: isHindi ? "अस्पताल नेटवर्क" : "Hospitals" },
    { href: "/register/hospital", label: isHindi ? "अस्पताल पंजीकरण" : "Register Hospital" },
    { href: "/application/status", label: isHindi ? "आवेदन ट्रैक करें" : "Track Application" },
    { href: "/contact", label: isHindi ? "संपर्क एवं सहायता" : "Contact & Help" },
  ];

  return (
    <header className="sticky top-0 z-50 bg-white border-b border-slate-200 shadow-xs">
      {/* Top Clinical Emerald & Navy Bar */}
      <div className="h-1 w-full bg-gradient-to-r from-teal-500 via-emerald-400 to-cyan-500" />

      {/* Official Top Utility Bar */}
      <div className="bg-[#07182F] text-slate-200 text-[11px] py-1.5 px-4 sm:px-6 border-b border-slate-800">
        <div className="max-w-7xl mx-auto flex flex-wrap items-center justify-between gap-2">
          {/* Emergency Ambulance & Prototype Disclaimer Strip */}
          <div className="flex items-center gap-2 sm:gap-3 text-slate-300">
            <span className="inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-bold bg-amber-500/20 text-amber-300 border border-amber-500/30">
              PROTOTYPE
            </span>
            <span className="text-[10px] text-slate-400 hidden md:inline">
              Smart India Hackathon Technical Prototype &bull;
            </span>
            <div className="flex items-center gap-1.5 text-emerald-400 font-semibold">
              <span className="flex h-1.5 w-1.5 rounded-full bg-emerald-400 animate-pulse-glow shrink-0" />
              <PhoneCall className="w-3 h-3 shrink-0" />
              <span>
                {isHindi ? "आपातकालीन:" : "Emergency:"}{" "}
                <strong className="text-white">108</strong>
              </span>
            </div>
            <span className="text-slate-600 hidden sm:inline">&bull;</span>
            <div className="hidden sm:flex items-center gap-1 text-teal-300 font-medium">
              <span>
                {isHindi ? "हेल्पलाइन:" : "Health Helpline:"}{" "}
                <strong className="text-white">1075</strong>
              </span>
            </div>
          </div>

          {/* Functional Language Toggle */}
          <div className="flex items-center gap-1 border-l border-slate-700 pl-3">
            <button
              type="button"
              onClick={() => handleLangToggle("en")}
              className={`px-2.5 py-1 rounded text-[11px] font-bold transition shadow-2xs ${
                currentLang === "en"
                  ? "bg-teal-600 text-white ring-1 ring-teal-400"
                  : "text-slate-300 hover:text-white hover:bg-slate-800"
              }`}
              aria-label="Switch to English"
            >
              English
            </button>
            <span className="text-slate-600">|</span>
            <button
              type="button"
              onClick={() => handleLangToggle("hi")}
              className={`px-2.5 py-1 rounded text-[11px] font-bold transition shadow-2xs ${
                currentLang === "hi"
                  ? "bg-teal-600 text-white ring-1 ring-teal-400"
                  : "text-slate-300 hover:text-white hover:bg-slate-800"
              }`}
              aria-label="Switch to Hindi"
            >
              हिन्दी
            </button>
          </div>
        </div>
      </div>

      {/* Main Navigation Bar */}
      <div className="max-w-7xl mx-auto px-4 sm:px-6">
        <div className="flex items-center justify-between h-16 sm:h-20">
          {/* Logo & Platform Identity */}
          <Link href="/" className="flex items-center gap-3 sm:gap-3.5 group">
            <div className="flex h-11 w-11 sm:h-12 sm:w-12 items-center justify-center rounded-xl bg-[#0B132B] text-white shadow-sm border border-slate-800 group-hover:bg-teal-900 transition">
              <Hospital className="w-6 h-6 text-teal-400" />
            </div>
            <div className="flex flex-col">
              <div className="flex items-center gap-2">
                <span className="text-lg sm:text-xl font-extrabold tracking-tight text-slate-900 group-hover:text-teal-700 transition">
                  ArogyaSetu Grid
                </span>
                <span className="rounded bg-teal-50 text-teal-800 border border-teal-300 px-1.5 py-0.5 text-[10px] font-bold uppercase tracking-wider hidden sm:inline-block">
                  {isHindi ? "राष्ट्रीय पोर्टल" : "National Portal"}
                </span>
              </div>
              <span className="text-[11px] sm:text-xs text-slate-500 font-medium tracking-tight">
                {isHindi ? "अस्पताल समन्वय एवं रेफरल पोर्टल" : "Hospital Coordination & Referral Portal"}
              </span>
            </div>
          </Link>

          {/* Desktop Navigation Links */}
          <nav className="hidden lg:flex items-center gap-1 xl:gap-2">
            {navLinks.map((link) => {
              const isActive = pathname === link.href;
              return (
                <Link
                  key={link.href}
                  href={link.href}
                  className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition ${
                    isActive
                      ? "text-teal-900 bg-teal-50 font-bold"
                      : "text-slate-700 hover:text-teal-700 hover:bg-slate-100"
                  }`}
                >
                  {link.label}
                </Link>
              );
            })}
          </nav>

          {/* Single Primary Action CTA */}
          <div className="hidden sm:flex items-center gap-2.5">
            {user ? (
              <div className="flex items-center gap-2.5">
                <span className="text-xs font-medium text-slate-600">
                  {isHindi ? "लॉगिन:" : "Signed in:"}{" "}
                  <strong className="text-slate-900">{user.username}</strong>
                </span>
                <Link
                  href="/"
                  className="rounded-lg bg-teal-700 text-white px-3.5 py-2 text-xs font-semibold hover:bg-teal-800 transition shadow-xs"
                >
                  {isHindi ? "डैशबोर्ड" : "My Dashboard"}
                </Link>
                <button
                  onClick={handleSignOut}
                  className="rounded-lg border border-slate-300 text-slate-700 px-3 py-2 text-xs font-semibold hover:bg-slate-100 transition"
                >
                  {isHindi ? "साइन आउट" : "Sign Out"}
                </button>
              </div>
            ) : (
              /* ONLY ONE clean primary login button */
              <Link
                href="/portal"
                className="rounded-xl bg-[#0B132B] px-4 py-2.5 text-xs font-bold text-white hover:bg-teal-800 transition shadow-sm flex items-center gap-2"
              >
                <LogIn className="w-3.5 h-3.5 text-teal-400" />
                <span>{isHindi ? "स्टाफ / विभाग लॉगिन" : "Staff / Department Login"}</span>
              </Link>
            )}
          </div>

          {/* Mobile Menu Trigger */}
          <div className="lg:hidden flex items-center gap-2">
            <Link
              href="/portal"
              className="rounded-lg bg-[#0B132B] text-white px-3 py-1.5 text-xs font-bold hover:bg-teal-800 transition"
            >
              {isHindi ? "लॉगिन" : "Login"}
            </Link>
            <button
              onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
              className="rounded-lg border border-slate-300 p-2 text-slate-700 hover:bg-slate-100"
              aria-label="Toggle navigation menu"
            >
              {mobileMenuOpen ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
            </button>
          </div>
        </div>
      </div>

      {/* Mobile Navigation Drawer */}
      {mobileMenuOpen && (
        <div className="lg:hidden border-t border-slate-200 bg-white px-4 pt-3 pb-6 space-y-3">
          <div className="flex flex-col space-y-1">
            {navLinks.map((link) => (
              <Link
                key={link.href}
                href={link.href}
                onClick={() => setMobileMenuOpen(false)}
                className="px-3 py-2 rounded-lg text-sm font-medium text-slate-700 hover:bg-slate-100 hover:text-teal-800"
              >
                {link.label}
              </Link>
            ))}
          </div>

          <div className="pt-3 border-t border-slate-200 space-y-2">
            <Link
              href="/portal"
              onClick={() => setMobileMenuOpen(false)}
              className="w-full flex items-center justify-center gap-2 rounded-lg bg-[#0B132B] text-white py-2.5 text-xs font-bold shadow-xs hover:bg-teal-800"
            >
              <LogIn className="w-4 h-4 text-teal-400" />
              <span>{isHindi ? "स्टाफ / विभाग लॉगिन" : "Staff / Department Login"}</span>
            </Link>
            <Link
              href="/register/hospital"
              onClick={() => setMobileMenuOpen(false)}
              className="w-full flex items-center justify-center gap-2 rounded-lg border border-slate-300 bg-slate-50 text-slate-700 py-2.5 text-xs font-semibold"
            >
              <FileCheck2 className="w-4 h-4 text-teal-700" />
              <span>{isHindi ? "अस्पताल पंजीकरण" : "Register Hospital"}</span>
            </Link>
            <Link
              href="/application/status"
              onClick={() => setMobileMenuOpen(false)}
              className="w-full flex items-center justify-center gap-2 rounded-lg border border-slate-200 bg-white text-slate-700 py-2 text-xs font-medium"
            >
              <span>{isHindi ? "आवेदन ट्रैक करें" : "Track Application"}</span>
            </Link>
          </div>
        </div>
      )}
    </header>
  );
};
