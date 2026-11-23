import React from "react";

export interface SwasthyaLogoProps {
  className?: string;
  size?: "sm" | "md" | "lg" | "xl";
  showText?: boolean;
  subtitle?: string;
  isHindi?: boolean;
  inverted?: boolean;
}

export const SwasthyaLogo: React.FC<SwasthyaLogoProps> = ({
  className = "",
  size = "md",
  showText = true,
  subtitle,
  isHindi = false,
  inverted = false,
}) => {
  const iconSizeClasses = {
    sm: "w-8 h-8",
    md: "w-10 h-10 sm:w-11 sm:h-11",
    lg: "w-12 h-12 sm:w-14 sm:h-14",
    xl: "w-16 h-16 sm:w-20 sm:h-20",
  };

  const titleSizeClasses = {
    sm: "text-sm",
    md: "text-base sm:text-lg",
    lg: "text-xl sm:text-2xl",
    xl: "text-2xl sm:text-3xl",
  };

  return (
    <div className={`flex items-center gap-3 ${className}`}>
      {/* Connected Network & Clinical Cross Icon */}
      <div
        className={`relative shrink-0 flex items-center justify-center rounded-xl transition duration-200 ${
          iconSizeClasses[size]
        } ${
          inverted
            ? "bg-[#07182F] border border-[#008F83]/40 shadow-sm"
            : "bg-[#07182F] text-white shadow-md border border-slate-800"
        }`}
      >
        <svg
          viewBox="0 0 32 32"
          fill="none"
          xmlns="http://www.w3.org/2000/svg"
          className="w-3/5 h-3/5"
        >
          {/* Outer Network Orbit */}
          <circle
            cx="16"
            cy="16"
            r="12"
            stroke="#008F83"
            strokeWidth="1.5"
            strokeDasharray="2 2"
            opacity="0.7"
          />
          {/* Healthcare Coordination Cross */}
          <path
            d="M13 8.5C13 8.22386 13.2239 8 13.5 8H18.5C18.7761 8 19 8.22386 19 8.5V13H23.5C23.7761 13 24 13.2239 24 13.5V18.5C24 18.7761 23.7761 19 23.5 19H19V23.5C19 23.7761 18.7761 24 18.5 24H13.5C13.2239 24 13 23.7761 13 23.5V19H8.5C8.22386 19 8 18.7761 8 18.5V13.5C8 13.2239 8.22386 13 8.5 13H13V8.5Z"
            fill="#008F83"
          />
          {/* Connected Network Nodes */}
          <circle cx="16" cy="4" r="1.75" fill="#00A99D" />
          <circle cx="16" cy="28" r="1.75" fill="#00A99D" />
          <circle cx="4" cy="16" r="1.75" fill="#00A99D" />
          <circle cx="28" cy="16" r="1.75" fill="#00A99D" />
          {/* Core Synchrony Point */}
          <circle cx="16" cy="16" r="2" fill="#FFFFFF" />
        </svg>
      </div>

      {showText && (
        <div className="flex flex-col">
          <div className="flex items-center gap-2">
            <span
              className={`font-black tracking-tight ${titleSizeClasses[size]} ${
                inverted ? "text-white" : "text-[#14243B]"
              }`}
            >
              {isHindi ? "स्वास्थ्य समन्वय" : "SWASTHYA SAMANVAY"}
            </span>
          </div>
          <span
            className={`text-[10px] sm:text-xs font-medium tracking-tight ${
              inverted ? "text-slate-300" : "text-[#60738C]"
            }`}
          >
            {subtitle ||
              (isHindi
                ? "राष्ट्रीय अस्पताल समन्वय एवं रेफरल प्लेटफॉर्म"
                : "National Hospital Coordination & Referral Platform")}
          </span>
        </div>
      )}
    </div>
  );
};
