"use client";

import React from "react";
import { Globe } from "lucide-react";
import { DepartmentLoginPage } from "@/components/auth/DepartmentLoginPage";

export default function CentralLoginPage() {
  return (
    <DepartmentLoginPage
      department="central"
      title="Central Health Command Login"
      subtitle="Sign in with your national healthcare administration credentials to access apex hospital approvals, nationwide capacity analytics, and system-wide monitoring."
      tier="National Tier • Apex Governance Access"
      expectedRole="CENTRAL_ADMIN"
      icon={Globe}
      accentColor={{
        bg: "bg-[#07182F]",
        text: "text-[#07182F]",
        border: "border-[#07182F]/30",
        button: "bg-[#07182F] hover:bg-[#0B2345]",
        lightBg: "bg-[#07182F]/10",
      }}
    />
  );
}
