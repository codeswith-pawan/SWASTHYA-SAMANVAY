"use client";

import React, { useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { Lock, Menu, X, ArrowRight, Activity } from "lucide-react";
import { SwasthyaLogo } from "@/components/shared/SwasthyaLogo";

export const RegistrationNavbar: React.FC = () => {
  const pathname = usePathname();
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  const navLinks = [
    { href: "/register", label: "Registration Hub" },
    { href: "/application/track", label: "Track Application" },
    { href: "/application/status", label: "Applicant Portal" },
    { href: "/reviewer", label: "Reviewer Portal" },
  ];

  return (
    <header className="sticky top-0 z-50 bg-[#07182F] text-white border-b border-[#0B2345] shadow-md">
      {/* Top Professional Utility Strip */}
      <div className="bg-[#040E1E] text-slate-300 text-[11px] py-1.5 px-4 sm:px-6 border-b border-slate-800/80">
        <div className="max-w-7xl mx-auto flex flex-wrap items-center justify-between gap-2">
          <div className="flex items-center gap-2">
            <span className="flex h-1.5 w-1.5 rounded-full bg-[#00A99D] animate-pulse-glow" />
            <span className="font-semibold text-slate-200">
              National Healthcare Onboarding & Accreditation Gateway
            </span>
            <span className="text-slate-600 hidden sm:inline">&bull;</span>
            <span className="text-slate-400 hidden sm:inline">
              Multi-Tier Hospital & Health Administration Verification
            </span>
          </div>
          <div className="flex items-center gap-3 text-slate-400 text-[11px]">
            <span>Technical Inquiries:</span>
            <a
              href="mailto:pawanbussiness108@gmail.com"
              className="text-[#00A99D] hover:text-white font-medium underline underline-offset-2"
            >
              pawanbussiness108@gmail.com
            </a>
          </div>
        </div>
      </div>

      {/* Main Header Bar */}
      <div className="max-w-7xl mx-auto px-4 sm:px-6">
        <div className="flex items-center justify-between h-16 sm:h-18">
          {/* Logo & Brand Identity */}
          <Link href="/" className="flex items-center gap-3 group">
            <SwasthyaLogo size="md" inverted={true} />
          </Link>

          {/* Desktop Navigation Links */}
          <nav className="hidden md:flex items-center gap-1 lg:gap-2">
            {navLinks.map((link) => {
              const isActive =
                pathname === link.href ||
                (link.href !== "/register" && pathname.startsWith(link.href));
              return (
                <Link
                  key={link.href}
                  href={link.href}
                  className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition ${
                    isActive
                      ? "bg-[#008F83] text-white shadow-sm font-bold"
                      : "text-slate-300 hover:text-white hover:bg-slate-800/60"
                  }`}
                >
                  {link.label}
                </Link>
              );
            })}
          </nav>

          {/* Primary Action Button */}
          <div className="hidden sm:flex items-center gap-3">
            <Link
              href="/portal"
              className="inline-flex items-center gap-2 rounded-xl bg-gradient-to-r from-[#008F83] to-[#00A99D] px-4 py-2 text-xs font-bold text-white hover:from-[#007A70] hover:to-[#008F83] transition shadow-md shadow-[#008F83]/20"
            >
              <Lock className="w-3.5 h-3.5" />
              <span>Department Portals</span>
            </Link>
          </div>

          {/* Mobile Menu Button */}
          <div className="flex md:hidden">
            <button
              onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
              className="p-2 rounded-lg text-slate-300 hover:text-white hover:bg-slate-800"
              aria-label="Toggle navigation"
            >
              {mobileMenuOpen ? <X className="w-6 h-6" /> : <Menu className="w-6 h-6" />}
            </button>
          </div>
        </div>
      </div>

      {/* Mobile Drawer */}
      {mobileMenuOpen && (
        <div className="md:hidden border-t border-slate-800 bg-[#07182F] px-4 pt-2 pb-6 space-y-3 shadow-xl">
          <nav className="flex flex-col space-y-1">
            {navLinks.map((link) => {
              const isActive =
                pathname === link.href ||
                (link.href !== "/register" && pathname.startsWith(link.href));
              return (
                <Link
                  key={link.href}
                  href={link.href}
                  onClick={() => setMobileMenuOpen(false)}
                  className={`px-3 py-2 rounded-lg text-xs font-semibold ${
                    isActive ? "bg-[#008F83] text-white font-bold" : "text-slate-300 hover:bg-slate-800"
                  }`}
                >
                  {link.label}
                </Link>
              );
            })}
          </nav>

          <div className="pt-2 border-t border-slate-800">
            <Link
              href="/portal"
              onClick={() => setMobileMenuOpen(false)}
              className="w-full inline-flex items-center justify-center gap-2 rounded-xl bg-[#008F83] py-2.5 text-xs font-bold text-white"
            >
              <Lock className="w-3.5 h-3.5" />
              <span>Department Portals</span>
            </Link>
          </div>
        </div>
      )}
    </header>
  );
};
