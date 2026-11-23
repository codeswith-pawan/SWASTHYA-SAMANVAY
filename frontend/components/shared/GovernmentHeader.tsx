"use client";

import React, { useState } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import {
  Menu,
  X,
  LogIn,
  ChevronRight,
  Shield,
  Activity,
} from "lucide-react";
import { getStoredUser, clearStoredSession } from "@/lib/api";
import { User } from "@/lib/types";
import { useLanguage } from "@/lib/i18n";
import { SwasthyaLogo } from "@/components/shared/SwasthyaLogo";

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
    { href: "/network", label: isHindi ? "अस्पताल नेटवर्क" : "Hospital Network" },
    { href: "/register/hospital", label: isHindi ? "अस्पताल पंजीकरण" : "Register Hospital" },
    { href: "/application/track", label: isHindi ? "आवेदन ट्रैक करें" : "Track Application" },
    { href: "/contact", label: isHindi ? "संपर्क एवं सहायता" : "Contact & Help" },
  ];

  return (
    <header className="sticky top-0 z-50 bg-white border-b border-[#DCE5EF] shadow-xs">
      {/* Top Clinical Emerald Accent Strip */}
      <div className="h-1 w-full bg-gradient-to-r from-[#008F83] via-[#00A99D] to-[#0B2345]" />

      {/* Clean Utility Bar */}
      <div className="bg-[#07182F] text-slate-200 text-[11px] py-1.5 px-4 sm:px-6 border-b border-slate-800">
        <div className="max-w-7xl mx-auto flex flex-wrap items-center justify-between gap-2">
          {/* Platform Domain Description */}
          <div className="flex items-center gap-2 text-slate-300">
            <span className="flex h-1.5 w-1.5 rounded-full bg-[#00A99D] animate-pulse-glow shrink-0" />
            <span className="font-semibold text-slate-200">
              {isHindi
                ? "राष्ट्रीय स्वास्थ्य सेवा समन्वय प्लेटफॉर्म"
                : "National Healthcare Coordination Platform"}
            </span>
            <span className="text-slate-600 hidden sm:inline">&bull;</span>
            <span className="text-slate-400 hidden sm:inline">
              {isHindi
                ? "अस्पताल संसाधन दृश्यता एवं रेफरल नेटवर्क"
                : "Hospital Resource Visibility & Referral Network"}
            </span>
          </div>

          {/* Functional Language Toggle */}
          <div className="flex items-center gap-1 border-l border-slate-700 pl-3">
            <button
              type="button"
              onClick={() => handleLangToggle("en")}
              className={`px-2.5 py-0.5 rounded text-[11px] font-bold transition ${
                currentLang === "en"
                  ? "bg-[#008F83] text-white ring-1 ring-teal-400"
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
              className={`px-2.5 py-0.5 rounded text-[11px] font-bold transition ${
                currentLang === "hi"
                  ? "bg-[#008F83] text-white ring-1 ring-teal-400"
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
          <Link href="/" className="group">
            <SwasthyaLogo isHindi={isHindi} size="md" />
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
                      ? "text-[#008F83] bg-[#008F83]/10 font-bold"
                      : "text-[#14243B] hover:text-[#008F83] hover:bg-[#F4F8FC]"
                  }`}
                >
                  {link.label}
                </Link>
              );
            })}
          </nav>

          {/* Primary Action CTA */}
          <div className="hidden sm:flex items-center gap-2.5">
            {user ? (
              <div className="flex items-center gap-2.5">
                <span className="text-xs font-medium text-[#60738C]">
                  {isHindi ? "लॉगिन:" : "Signed in:"}{" "}
                  <strong className="text-[#14243B]">{user.username}</strong>
                </span>
                <Link
                  href="/"
                  className="rounded-lg bg-[#008F83] text-white px-3.5 py-2 text-xs font-semibold hover:bg-[#007A70] transition shadow-xs"
                >
                  {isHindi ? "डैशबोर्ड" : "My Dashboard"}
                </Link>
                <button
                  onClick={handleSignOut}
                  className="rounded-lg border border-[#DCE5EF] text-[#14243B] px-3 py-2 text-xs font-semibold hover:bg-[#F4F8FC] transition"
                >
                  {isHindi ? "साइन आउट" : "Sign Out"}
                </button>
              </div>
            ) : (
              <Link
                href="/portal"
                className="rounded-xl bg-[#0B2345] px-4 py-2.5 text-xs font-bold text-white hover:bg-[#07182F] transition shadow-xs flex items-center gap-2"
              >
                <LogIn className="w-3.5 h-3.5 text-[#00A99D]" />
                <span>{isHindi ? "स्टाफ / विभाग लॉगिन" : "Staff / Department Login"}</span>
              </Link>
            )}
          </div>

          {/* Mobile Menu Toggle Button */}
          <div className="flex lg:hidden items-center gap-2">
            <button
              onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
              className="p-2 rounded-lg text-slate-700 hover:text-slate-900 hover:bg-slate-100 transition"
              aria-label="Toggle navigation menu"
            >
              {mobileMenuOpen ? <X className="w-6 h-6" /> : <Menu className="w-6 h-6" />}
            </button>
          </div>
        </div>
      </div>

      {/* Mobile Drawer Menu */}
      {mobileMenuOpen && (
        <div className="lg:hidden border-t border-[#DCE5EF] bg-white px-4 pt-3 pb-6 space-y-3 shadow-lg">
          <nav className="flex flex-col space-y-1">
            {navLinks.map((link) => {
              const isActive = pathname === link.href;
              return (
                <Link
                  key={link.href}
                  href={link.href}
                  onClick={() => setMobileMenuOpen(false)}
                  className={`px-3 py-2.5 rounded-lg text-sm font-semibold transition flex items-center justify-between ${
                    isActive
                      ? "text-[#008F83] bg-[#008F83]/10 font-bold"
                      : "text-[#14243B] hover:text-[#008F83] hover:bg-[#F4F8FC]"
                  }`}
                >
                  <span>{link.label}</span>
                  <ChevronRight className="w-4 h-4 text-slate-400" />
                </Link>
              );
            })}
          </nav>

          <div className="pt-3 border-t border-slate-100 flex flex-col gap-2">
            {user ? (
              <>
                <Link
                  href="/"
                  onClick={() => setMobileMenuOpen(false)}
                  className="w-full text-center rounded-xl bg-[#008F83] px-4 py-2.5 text-xs font-bold text-white shadow-xs"
                >
                  {isHindi ? "डैशबोर्ड पर जाएं" : "Go to Dashboard"}
                </Link>
                <button
                  onClick={() => {
                    handleSignOut();
                    setMobileMenuOpen(false);
                  }}
                  className="w-full text-center rounded-xl border border-slate-300 px-4 py-2 text-xs font-semibold text-slate-700"
                >
                  {isHindi ? "साइन आउट" : "Sign Out"}
                </button>
              </>
            ) : (
              <Link
                href="/portal"
                onClick={() => setMobileMenuOpen(false)}
                className="w-full text-center rounded-xl bg-[#0B2345] px-4 py-2.5 text-xs font-bold text-white shadow-xs flex items-center justify-center gap-2"
              >
                <LogIn className="w-4 h-4 text-[#00A99D]" />
                <span>{isHindi ? "स्टाफ / विभाग लॉगिन" : "Staff / Department Login"}</span>
              </Link>
            )}
          </div>
        </div>
      )}
    </header>
  );
};
