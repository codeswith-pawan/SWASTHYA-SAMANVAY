"use client";

import React from "react";
import { Building2 } from "lucide-react";
import { DepartmentLoginPage } from "@/components/auth/DepartmentLoginPage";

export default function HospitalLoginPage() {
  return (
    <DepartmentLoginPage
      department="hospital"
      title="Hospital Operations Login"
      subtitle="Sign in with your hospital staff or medical superintendent credentials to manage emergency bed allocation, ICU inventory, and clinical referrals."
      tier="Facility Tier • Restricted Access"
      expectedRole="HOSPITAL"
      icon={Building2}
      accentColor={{
        bg: "bg-[#008F83]",
        text: "text-[#008F83]",
        border: "border-[#008F83]/30",
        button: "bg-[#0B2345] hover:bg-[#07182F]",
        lightBg: "bg-[#008F83]/10",
      }}
    />
  );
}
