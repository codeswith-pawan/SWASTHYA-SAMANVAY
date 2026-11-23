import React from "react";
import { User, NotificationItem } from "@/lib/types";
import { NotificationPanel } from "./NotificationPanel";
import { clearStoredSession } from "@/lib/api";

export interface TabItem {
  id: string;
  label: string;
  icon?: string;
  badge?: number | string;
}

interface DashboardLayoutProps {
  user: User;
  tierBadge: {
    label: string;
    color: "blue" | "indigo" | "teal" | "purple";
  };
  title: string;
  subtitle?: string;
  headerAction?: React.ReactNode;
  tabs?: TabItem[];
  activeTab?: string;
  onTabChange?: (tabId: string) => void;
  onRefresh?: () => void;
  refreshLoading?: boolean;
  notifications?: NotificationItem[];
  unreadCount?: number;
  notifLoading?: boolean;
  onMarkNotifRead?: (id: string) => void;
  onMarkAllNotifsRead?: () => void;
  children: React.ReactNode;
}

export const DashboardLayout: React.FC<DashboardLayoutProps> = ({
  user,
  tierBadge,
  title,
  subtitle,
  headerAction,
  tabs = [],
  activeTab,
  onTabChange,
  onRefresh,
  refreshLoading = false,
  notifications,
  unreadCount = 0,
  notifLoading = false,
  onMarkNotifRead,
  onMarkAllNotifsRead,
  children,
}) => {
  const handleSignOut = () => {
    clearStoredSession();
    window.location.reload();
  };

  const badgeColorStyles = {
    blue: "bg-blue-500/10 text-blue-400 border-blue-500/20",
    indigo: "bg-indigo-500/10 text-indigo-400 border-indigo-500/20",
    teal: "bg-teal-500/10 text-teal-400 border-teal-500/20",
    purple: "bg-purple-500/10 text-purple-400 border-purple-500/20",
  }[tierBadge.color];

  return (
    <div className="min-h-screen bg-slate-950 text-white flex flex-col font-sans">
      {/* Sticky Header */}
      <header className="sticky top-0 z-40 border-b border-slate-800 bg-slate-900/95 backdrop-blur-md">
        <div className="mx-auto max-w-7xl px-4 sm:px-6 py-3.5">
          <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
            {/* Title & Metadata */}
            <div className="flex items-start gap-3">
              <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-slate-800 text-xl shadow-inner border border-slate-700">
                🏥
              </div>
              <div>
                <div className="flex flex-wrap items-center gap-2">
                  <span
                    className={`rounded-full px-2.5 py-0.5 text-[11px] font-semibold tracking-wide border uppercase ${badgeColorStyles}`}
                  >
                    {tierBadge.label}
                  </span>
                  <h1 className="text-lg font-bold tracking-tight text-white sm:text-xl">
                    {title}
                  </h1>
                </div>
                <p className="mt-0.5 text-xs text-slate-400">
                  {subtitle || `${user.name} • ${user.role}`}
                </p>
              </div>
            </div>

            {/* Action Bar */}
            <div className="flex items-center gap-2.5 self-end md:self-auto">
              {headerAction}

              {notifications && onMarkNotifRead && onMarkAllNotifsRead && onRefresh && (
                <NotificationPanel
                  notifications={notifications}
                  unreadCount={unreadCount}
                  loading={notifLoading}
                  onMarkRead={onMarkNotifRead}
                  onMarkAllRead={onMarkAllNotifsRead}
                  onRefresh={onRefresh}
                />
              )}

              {onRefresh && (
                <button
                  onClick={onRefresh}
                  disabled={refreshLoading}
                  className="flex items-center gap-1.5 rounded-xl border border-slate-700 bg-slate-800 px-3 py-2 text-xs font-medium text-slate-300 hover:bg-slate-700 hover:text-white transition disabled:opacity-50"
                  title="Refresh Dashboard Data"
                >
                  <span
                    className={`text-xs ${
                      refreshLoading ? "animate-spin" : ""
                    }`}
                  >
                    🔄
                  </span>
                  <span className="hidden sm:inline">
                    {refreshLoading ? "Syncing..." : "Refresh"}
                  </span>
                </button>
              )}

              <button
                onClick={handleSignOut}
                className="flex items-center gap-1.5 rounded-xl border border-rose-500/30 bg-rose-500/10 px-3 py-2 text-xs font-semibold text-rose-300 hover:bg-rose-500/20 transition"
                title="End Authenticated Session"
              >
                <span>🚪</span>
                <span>Sign Out</span>
              </button>
            </div>
          </div>

          {/* Navigation Tabs (Horizontal Scroll Safe on Mobile) */}
          {tabs.length > 0 && onTabChange && (
            <div className="mt-3.5 flex gap-1.5 overflow-x-auto border-t border-slate-800/80 pt-2 pb-0.5 scrollbar-none">
              {tabs.map((tab) => {
                const isActive = activeTab === tab.id;
                return (
                  <button
                    key={tab.id}
                    onClick={() => onTabChange(tab.id)}
                    className={`flex shrink-0 items-center gap-2 rounded-lg px-3.5 py-1.5 text-xs font-semibold transition ${
                      isActive
                        ? "bg-slate-800 text-white shadow-sm ring-1 ring-slate-700"
                        : "text-slate-400 hover:bg-slate-800/50 hover:text-slate-200"
                    }`}
                  >
                    {tab.icon && <span>{tab.icon}</span>}
                    <span>{tab.label}</span>
                    {tab.badge !== undefined && (
                      <span
                        className={`rounded-full px-2 py-0.2 text-[10px] font-bold ${
                          isActive
                            ? "bg-blue-600 text-white"
                            : "bg-slate-800 text-slate-400"
                        }`}
                      >
                        {tab.badge}
                      </span>
                    )}
                  </button>
                );
              })}
            </div>
          )}
        </div>
      </header>

      {/* Main Body */}
      <main className="flex-1 mx-auto w-full max-w-7xl px-4 sm:px-6 py-6 sm:py-8">
        {children}
      </main>

      {/* Footer */}
      <footer className="border-t border-slate-800/80 bg-slate-900/60 py-4 text-center text-xs text-slate-400">
        <div className="mx-auto max-w-7xl px-4 sm:px-6 flex flex-col sm:flex-row items-center justify-between gap-2">
          <p>
            SWASTHYA SAMANVAY • Hospital Coordination & Referral Platform
          </p>
          <p className="text-[11px] text-slate-400">
            Clinical Decision Support (CDS) only. All patient admissions require physician confirmation.
          </p>
        </div>
      </footer>
    </div>
  );
};
