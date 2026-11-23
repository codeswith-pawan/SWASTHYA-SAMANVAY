"use client";

import React, { createContext, useContext, useEffect, useState } from "react";

export type Language = "en" | "hi";

export interface LanguageContextType {
  lang: Language;
  setLang: (lang: Language) => void;
  isHindi: boolean;
  t: (enText: string, hiText: string) => string;
}

const STORAGE_KEY = "swasthya_samanvay_lang";
const LEGACY_STORAGE_KEY = "arogyasetu_lang";

const LanguageContext = createContext<LanguageContextType>({
  lang: "en",
  setLang: () => {},
  isHindi: false,
  t: (enText: string) => enText,
});

export const LanguageProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [lang, setLangState] = useState<Language>("en");
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    try {
      const saved = localStorage.getItem(STORAGE_KEY) || localStorage.getItem(LEGACY_STORAGE_KEY);
      if (saved === "en" || saved === "hi") {
        setLangState(saved);
      }
    } catch {
      // Ignore localStorage errors (e.g., privacy mode)
    }
    setMounted(true);
  }, []);

  const setLang = (newLang: Language) => {
    setLangState(newLang);
    try {
      localStorage.setItem(STORAGE_KEY, newLang);
    } catch {
      // Ignore localStorage errors
    }
  };

  const isHindi = lang === "hi";

  const t = (enText: string, hiText: string) => {
    return isHindi ? hiText : enText;
  };

  return (
    <LanguageContext.Provider value={{ lang, setLang, isHindi, t }}>
      {children}
    </LanguageContext.Provider>
  );
};

export const useLanguage = (): LanguageContextType => {
  const context = useContext(LanguageContext);
  if (!context) {
    throw new Error("useLanguage must be used within a LanguageProvider");
  }
  return context;
};
