"use client";
import { useState } from "react";
import { motion } from "framer-motion";
import {
  Bell, Globe, Palette, Lock, User2, ChevronRight,
  Check, Sun, Moon, Monitor, Download, Trash2
} from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Separator } from "@/components/ui/separator";
import { Badge } from "@/components/ui/badge";
import { Switch } from "@/components/ui/switch";
import { usePreferences } from "@/lib/hooks/usePreferences";
import { useAuthStore } from "@/lib/stores/auth.store";

const anim = (i: number) => ({
  initial: { opacity: 0, y: 16 },
  animate: { opacity: 1, y: 0 },
  transition: { delay: i * 0.07, duration: 0.4, ease: [0.23, 1, 0.32, 1] as const },
});

// ── Notification Settings ─────────────────────────────────────────────────────
function NotificationsCard() {
  const { preferences, update, isUpdating } = usePreferences();

  const items = [
    { key: "email_recommendations",  label: "Style recommendations",     desc: "Personalised product and outfit picks", locked: false },
    { key: "email_marketing",         label: "News & announcements",      desc: "New features, brand partnerships",       locked: false },
    { key: "email_product_updates",   label: "Product updates",           desc: "Important platform changes",             locked: false },
    { key: "email_security_alerts",   label: "Security alerts",           desc: "Login attempts and account changes",     locked: true  },
    { key: "push_recommendations",    label: "Push: recommendations",     desc: "Mobile push for style picks",            locked: false },
    { key: "push_tryon_complete",     label: "Push: try-on complete",     desc: "When your virtual try-on is ready",      locked: false },
    { key: "push_scan_complete",      label: "Push: scan complete",       desc: "When your facial analysis is ready",     locked: false },
    { key: "in_app_notifications",    label: "In-app notifications",      desc: "Notification bell in dashboard",         locked: false },
  ] as const;

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-base">
          <Bell className="h-4 w-4 text-brand-gold" /> Notifications
        </CardTitle>
        <CardDescription>Choose which updates you want to receive.</CardDescription>
      </CardHeader>
      <CardContent className="space-y-1">
        {items.map(({ key, label, desc, locked }, i) => (
          <div key={key}>
            <div className="flex items-center justify-between gap-4 py-3">
              <div className="min-w-0">
                <div className="flex items-center gap-2">
                  <span className="text-sm font-medium text-foreground">{label}</span>
                  {locked && <Badge variant="default" className="text-2xs">Required</Badge>}
                </div>
                <p className="text-xs text-muted-foreground/60 mt-0.5">{desc}</p>
              </div>
              <Switch
                checked={preferences?.[key] ?? true}
                disabled={isUpdating || locked}
                onCheckedChange={(v) => update({ [key]: v })}
              />
            </div>
            {i < items.length - 1 && <Separator />}
          </div>
        ))}
      </CardContent>
    </Card>
  );
}

// ── Display Settings ──────────────────────────────────────────────────────────
function DisplayCard() {
  const { preferences, update, isUpdating } = usePreferences();

  const themes = [
    { value: "dark",   label: "Dark",   icon: Moon },
    { value: "light",  label: "Light",  icon: Sun },
    { value: "system", label: "System", icon: Monitor },
  ];

  const currencies = ["USD", "EUR", "GBP", "INR", "JPY", "CAD", "AUD"];
  const units      = [{ value: "metric", label: "Metric (cm, kg)" }, { value: "imperial", label: "Imperial (in, lbs)" }];

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-base">
          <Palette className="h-4 w-4 text-brand-gold" /> Display & Region
        </CardTitle>
        <CardDescription>Personalise your AuraFit experience.</CardDescription>
      </CardHeader>
      <CardContent className="space-y-6">
        {/* Theme */}
        <div>
          <label className="text-xs font-medium tracking-wide text-muted-foreground/60 uppercase block mb-3">Theme</label>
          <div className="flex gap-2">
            {themes.map(({ value, label, icon: Icon }) => (
              <button key={value}
                onClick={() => update({ theme: value })}
                disabled={isUpdating}
                className={`flex flex-1 flex-col items-center gap-1.5 rounded-xl border py-3 text-xs transition-all ${preferences?.theme === value ? "border-brand-gold/40 bg-brand-gold/8 text-brand-gold" : "border-white/[0.06] text-muted-foreground/60 hover:border-white/[0.1] hover:text-foreground/80"}`}
              >
                <Icon className="h-4 w-4" />
                {label}
                {preferences?.theme === value && <Check className="h-3 w-3" />}
              </button>
            ))}
          </div>
        </div>

        <Separator />

        {/* Currency */}
        <div>
          <label className="text-xs font-medium tracking-wide text-muted-foreground/60 uppercase block mb-3">Currency</label>
          <div className="flex flex-wrap gap-2">
            {currencies.map(c => (
              <button key={c}
                onClick={() => update({ currency: c })}
                disabled={isUpdating}
                className={`rounded-lg border px-3 py-1.5 text-xs font-medium transition-all ${preferences?.currency === c ? "border-brand-gold/40 bg-brand-gold/10 text-brand-gold" : "border-white/[0.06] text-muted-foreground/60 hover:border-white/[0.1]"}`}
              >
                {c}
              </button>
            ))}
          </div>
        </div>

        <Separator />

        {/* Measurement unit */}
        <div>
          <label className="text-xs font-medium tracking-wide text-muted-foreground/60 uppercase block mb-3">Measurements</label>
          <div className="flex gap-2">
            {units.map(({ value, label }) => (
              <button key={value}
                onClick={() => update({ measurement_unit: value })}
                disabled={isUpdating}
                className={`flex-1 rounded-xl border px-4 py-2.5 text-sm text-left transition-all ${preferences?.measurement_unit === value ? "border-brand-gold/40 bg-brand-gold/8 text-brand-gold" : "border-white/[0.06] text-muted-foreground/60 hover:border-white/[0.1]"}`}
              >
                {label}
              </button>
            ))}
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

// ── Privacy Settings ──────────────────────────────────────────────────────────
function PrivacyCard() {
  const { preferences, update, isUpdating } = usePreferences();

  const items = [
    {
      key: "profile_public",
      label: "Public profile",
      desc: "Allow other users to discover your style profile and public outfits",
    },
    {
      key: "allow_personalisation",
      label: "Personalised recommendations",
      desc: "Use your interaction data to improve style and beauty recommendations",
    },
    {
      key: "allow_data_training",
      label: "Contribute to AI training",
      desc: "Help improve AuraFit's AI models — your data is always anonymised",
    },
  ] as const;

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-base">
          <Lock className="h-4 w-4 text-brand-gold" /> Privacy
        </CardTitle>
        <CardDescription>Control how your data is used and shared.</CardDescription>
      </CardHeader>
      <CardContent className="space-y-1">
        {items.map(({ key, label, desc }, i) => (
          <div key={key}>
            <div className="flex items-center justify-between gap-4 py-3">
              <div className="min-w-0">
                <span className="text-sm font-medium text-foreground">{label}</span>
                <p className="text-xs text-muted-foreground/60 mt-0.5">{desc}</p>
              </div>
              <Switch
                checked={preferences?.[key] ?? false}
                disabled={isUpdating}
                onCheckedChange={(v) => update({ [key]: v })}
              />
            </div>
            {i < items.length - 1 && <Separator />}
          </div>
        ))}
      </CardContent>
    </Card>
  );
}

// ── Data & Account Card ───────────────────────────────────────────────────────
function DataCard() {
  const [exporting, setExporting] = useState(false);
  const [exportDone, setExportDone] = useState(false);

  const handleExport = async () => {
    setExporting(true);
    try {
      const { usersApi } = await import("@/lib/api/users");
      await usersApi.requestDataExport({ include_interactions: true, include_scan_data: true, include_chat_history: false });
      setExportDone(true);
      setTimeout(() => setExportDone(false), 8000);
    } finally {
      setExporting(false);
    }
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-base">
          <User2 className="h-4 w-4 text-brand-gold" /> Your Data
        </CardTitle>
        <CardDescription>Download or manage your AuraFit data in compliance with GDPR.</CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        {exportDone && (
          <motion.div initial={{ opacity: 0, scale: 0.96 }} animate={{ opacity: 1, scale: 1 }}
            className="flex items-center gap-2 rounded-xl border border-emerald-500/20 bg-emerald-500/10 px-4 py-3 text-sm text-emerald-400">
            <Check className="h-4 w-4" /> Export queued — you'll receive an email when it's ready.
          </motion.div>
        )}
        <div className="flex items-center justify-between gap-4 rounded-xl border border-white/[0.06] p-4">
          <div>
            <p className="text-sm font-medium">Export your data</p>
            <p className="text-xs text-muted-foreground/60 mt-0.5">Download a copy of your profile, interactions, and style history.</p>
          </div>
          <Button variant="ghost-gold" size="sm" loading={exporting} onClick={handleExport}>
            <Download className="h-3.5 w-3.5" /> Export
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}

// ── Main Settings Page ────────────────────────────────────────────────────────
export default function SettingsPage() {
  return (
    <div className="max-w-3xl space-y-8">
      <motion.div {...anim(0)}>
        <h1 className="font-display text-display-md font-light tracking-tightest">Settings</h1>
        <p className="mt-1.5 text-muted-foreground">Manage your notification preferences, display settings, and privacy options.</p>
      </motion.div>

      <motion.div {...anim(1)}><NotificationsCard /></motion.div>
      <motion.div {...anim(2)}><DisplayCard /></motion.div>
      <motion.div {...anim(3)}><PrivacyCard /></motion.div>
      <motion.div {...anim(4)}><DataCard /></motion.div>
    </div>
  );
}
