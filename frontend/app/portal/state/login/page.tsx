"use client";

import React from "react";
import { ShieldCheck } from "lucide-react";
import { DepartmentLoginPage } from "@/components/auth/DepartmentLoginPage";

export default function StateLoginPage() {
  return (
    <DepartmentLoginPage
      department="state"
      title="State Health Directorate Login"
      subtitle="Sign in with your state health directorate credentials to manage inter-district transfer logistics, review escalated applications, and view state-wide healthcare metrics."
      tier="State Tier • Directorate Access"
      expectedRole="STATE_ADMIN"
      icon={ShieldCheck}
      accentColor={{
        bg: "bg-[#008F83]",
        text: "text-[#008F83]",
        border: "border-[#008F83]/30",
        button: "bg-[#008F83] hover:bg-[#007A70]",
        lightBg: "bg-[#008F83]/10",
      }}
    />
  );
}
