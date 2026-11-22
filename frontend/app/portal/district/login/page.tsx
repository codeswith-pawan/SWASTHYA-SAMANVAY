"use client";

import React from "react";
import { MapPin } from "lucide-react";
import { DepartmentLoginPage } from "@/components/auth/DepartmentLoginPage";

export default function DistrictLoginPage() {
  return (
    <DepartmentLoginPage
      department="district"
      title="District Health Authority Login"
      subtitle="Sign in with your district health office credentials to monitor network facilities, review accreditation applications, and oversee local bed capacity."
      tier="District Tier • Administrative Access"
      expectedRole="DISTRICT_ADMIN"
      icon={MapPin}
      accentColor={{
        bg: "bg-[#0B2345]",
        text: "text-[#0B2345]",
        border: "border-[#0B2345]/30",
        button: "bg-[#0B2345] hover:bg-[#07182F]",
        lightBg: "bg-[#0B2345]/10",
      }}
    />
  );
}
