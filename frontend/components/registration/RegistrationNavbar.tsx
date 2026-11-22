"use client";

import React, { useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { Hospital, Lock, Shield, Menu, X, ArrowRight, AlertCircle, PhoneCall } from "lucide-react";

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
      {/* Top Prototype Disclaimer Strip */}
      <div className="bg-[#040E1E] text-slate-300 text-[11px] py-1 px-4 sm:px-6 border-b border-slate-800/80">
        <div className="max-w-7xl mx-auto flex flex-wrap items-center justify-between gap-2">
          <div className="flex items-center gap-2">
            <span className="inline-flex items-center px-2 py-0.5 rounded text-[10px] font-bold bg-amber-500/20 text-amber-300 border border-amber-500/30">
              PROTOTYPE
            </span>
            <span className="text-slate-300">
              Smart India Hackathon Technical Prototype &bull; Not an official Government of India portal.
            </span>
          </div>
          <div className="hidden sm:flex items-center gap-3 text-slate-400">
            <span className="flex items-center gap-1.5 text-emerald-400 font-semibold">
              <span className="h-1.5 w-1.5 rounded-full bg-emerald-400 animate-pulse-glow" />
              Emergency Ambulance: <strong className="text-white">108</strong>
            </span>
            <span>&bull;</span>
            <span className="text-teal-300 font-medium">
              National Health Helpline: <strong className="text-white">1075</strong>
            </span>
          </div>
        </div>
      </div>

      {/* Main Header Bar */}
      <div className="max-w-7xl mx-auto px-4 sm:px-6">
        <div className="flex items-center justify-between h-16 sm:h-18">
          {/* Logo & Brand Identity */}
          <Link href="/" className="flex items-center gap-3 group">
            <div className="flex h-10 w-10 sm:h-11 sm:w-11 items-center justify-center rounded-xl bg-gradient-to-br from-[#008F83] to-[#00A99D] text-white shadow-md shadow-[#008F83]/20 group-hover:scale-105 transition-transform duration-200">
              <Hospital className="w-5 h-5 sm:w-6 sm:h-6 text-white" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span className="text-base sm:text-lg font-extrabold tracking-tight text-white group-hover:text-teal-300 transition">
                  ArogyaSetu Grid
                </span>
                <span className="hidden sm:inline-block rounded-full bg-[#008F83]/20 border border-[#008F83]/40 px-2 py-0.5 text-[10px] font-bold text-teal-300 uppercase tracking-wider">
                  Healthcare Grid
                </span>
              </div>
              <p className="text-[11px] text-slate-400">
                Hospital Coordination & Referral Portal
              </p>
            </div>
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
          <div className="flex md:hidden items-center gap-2">
            <button
              type="button"
              onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
              className="p-2 rounded-lg bg-slate-800 text-slate-200 hover:text-white"
              aria-label="Toggle navigation menu"
            >
              {mobileMenuOpen ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
            </button>
          </div>
        </div>
      </div>

      {/* Mobile Drawer */}
      {mobileMenuOpen && (
        <div className="md:hidden border-t border-slate-800 bg-[#07182F] px-4 py-4 space-y-2 animate-fade-in-up">
          {navLinks.map((link) => {
            const isActive =
              pathname === link.href ||
              (link.href !== "/register" && pathname.startsWith(link.href));
            return (
              <Link
                key={link.href}
                href={link.href}
                onClick={() => setMobileMenuOpen(false)}
                className={`block px-3 py-2 rounded-lg text-xs font-semibold ${
                  isActive
                    ? "bg-[#008F83] text-white font-bold"
                    : "text-slate-300 hover:bg-slate-800"
                }`}
              >
                {link.label}
              </Link>
            );
          })}
          <div className="pt-2 border-t border-slate-800">
            <Link
              href="/portal"
              onClick={() => setMobileMenuOpen(false)}
              className="flex items-center justify-center gap-2 w-full rounded-xl bg-gradient-to-r from-[#008F83] to-[#00A99D] px-4 py-2.5 text-xs font-bold text-white"
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
