"use client";
import { useState } from "react";
import { motion } from "framer-motion";
import {
  Shield, Smartphone, Monitor, Tablet, LogOut, AlertTriangle,
  Key, QrCode, CheckCircle, Lock, Eye, EyeOff, Trash2, MapPin, Clock
} from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import { Progress } from "@/components/ui/progress";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from "@/components/ui/dialog";
import { useSessions } from "@/lib/hooks/useSessions";
import { useAuth } from "@/lib/hooks/useAuth";
import { authExtendedApi, sessionsApi } from "@/lib/api/users";
import { useAuthStore } from "@/lib/stores/auth.store";
import { useQuery } from "@tanstack/react-query";
import { usersApi } from "@/lib/api/users";
import type { UserSession } from "@/types";

const anim = (i: number) => ({
  initial: { opacity: 0, y: 16 },
  animate: { opacity: 1, y: 0 },
  transition: { delay: i * 0.08, duration: 0.4, ease: [0.23, 1, 0.32, 1] as const },
});

function DeviceIcon({ type }: { type: string | null }) {
  if (type === "mobile") return <Smartphone className="h-4 w-4" />;
  if (type === "tablet") return <Tablet className="h-4 w-4" />;
  return <Monitor className="h-4 w-4" />;
}

function timeAgo(dateStr: string | null): string {
  if (!dateStr) return "Unknown";
  const diff = Date.now() - new Date(dateStr).getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 1) return "Just now";
  if (mins < 60) return `${mins}m ago`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs}h ago`;
  return `${Math.floor(hrs / 24)}d ago`;
}

// ── Password Change Card ──────────────────────────────────────────────────────
function PasswordCard() {
  const [current, setCurrent] = useState("");
  const [next, setNext]       = useState("");
  const [confirm, setConfirm] = useState("");
  const [showCurrent, setShowCurrent] = useState(false);
  const [showNext, setShowNext]       = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError]     = useState("");
  const [success, setSuccess] = useState(false);

  const strength = (() => {
    let s = 0;
    if (next.length >= 8) s++;
    if (/[A-Z]/.test(next)) s++;
    if (/[0-9]/.test(next)) s++;
    if (/[^A-Za-z0-9]/.test(next)) s++;
    return s;
  })();

  const strengthLabel = ["", "Weak", "Fair", "Good", "Strong"][strength];
  const strengthColor = ["", "bg-destructive", "bg-amber-500", "bg-yellow-400", "bg-emerald-500"][strength];

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (next !== confirm) { setError("Passwords do not match"); return; }
    if (strength < 2) { setError("Please choose a stronger password"); return; }
    setLoading(true); setError("");
    try {
      await authExtendedApi.changePassword(current, next);
      setSuccess(true);
      setCurrent(""); setNext(""); setConfirm("");
      setTimeout(() => setSuccess(false), 4000);
    } catch (err: any) {
      setError(err?.response?.data?.detail?.message ?? "Failed to change password");
    } finally {
      setLoading(false);
    }
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-base">
          <Key className="h-4 w-4 text-brand-gold" /> Change Password
        </CardTitle>
        <CardDescription>Use a strong password with uppercase, numbers, and symbols.</CardDescription>
      </CardHeader>
      <CardContent>
        {success && (
          <motion.div initial={{ opacity: 0, scale: 0.96 }} animate={{ opacity: 1, scale: 1 }}
            className="mb-5 flex items-center gap-2 rounded-xl border border-emerald-500/20 bg-emerald-500/10 px-4 py-3 text-sm text-emerald-400">
            <CheckCircle className="h-4 w-4" /> Password changed successfully. All other sessions revoked.
          </motion.div>
        )}
        {error && (
          <div className="mb-5 rounded-xl border border-destructive/20 bg-destructive/10 px-4 py-3 text-sm text-destructive">{error}</div>
        )}
        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="relative">
            <Input label="Current password" type={showCurrent ? "text" : "password"}
              value={current} onChange={e => setCurrent(e.target.value)} required />
            <button type="button" onClick={() => setShowCurrent(!showCurrent)}
              className="absolute right-3 top-8 text-muted-foreground/40 hover:text-muted-foreground">
              {showCurrent ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
            </button>
          </div>

          <div className="relative">
            <Input label="New password" type={showNext ? "text" : "password"}
              value={next} onChange={e => setNext(e.target.value)} required />
            <button type="button" onClick={() => setShowNext(!showNext)}
              className="absolute right-3 top-8 text-muted-foreground/40 hover:text-muted-foreground">
              {showNext ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
            </button>
          </div>

          {next && (
            <div className="space-y-1">
              <div className="flex items-center justify-between text-xs">
                <span className="text-muted-foreground/60">Strength</span>
                <span className={strength >= 3 ? "text-emerald-400" : "text-muted-foreground/60"}>{strengthLabel}</span>
              </div>
              <div className="flex gap-1">
                {[1, 2, 3, 4].map(i => (
                  <div key={i} className={`h-1 flex-1 rounded-full transition-all duration-300 ${i <= strength ? strengthColor : "bg-white/[0.06]"}`} />
                ))}
              </div>
            </div>
          )}

          <Input label="Confirm new password" type="password"
            value={confirm} onChange={e => setConfirm(e.target.value)} required />

          <Button type="submit" variant="gold" loading={loading} className="w-full sm:w-auto">
            Update Password
          </Button>
        </form>
      </CardContent>
    </Card>
  );
}

// ── MFA Card ──────────────────────────────────────────────────────────────────
function MFACard() {
  const { user } = useAuthStore();
  const mfaEnabled = user?.mfa_enabled ?? false;
  const [setupOpen, setSetupOpen] = useState(false);
  const [disableOpen, setDisableOpen] = useState(false);
  const [qrData, setQrData]   = useState<{ secret: string; qr_code_url: string; backup_codes: string[] } | null>(null);
  const [confirmCode, setConfirmCode] = useState("");
  const [disablePassword, setDisablePassword] = useState("");
  const [disableCode, setDisableCode]         = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError]     = useState("");
  const [step, setStep]       = useState<"qr" | "backup" | "done">("qr");

  const startSetup = async () => {
    setLoading(true); setError("");
    try {
      const { data } = await authExtendedApi.setupMFA();
      if (data.data) { setQrData(data.data); setSetupOpen(true); setStep("qr"); }
    } catch { setError("Failed to start MFA setup"); }
    finally { setLoading(false); }
  };

  const confirmSetup = async () => {
    setLoading(true); setError("");
    try {
      await authExtendedApi.confirmMFA(confirmCode);
      setStep("backup");
    } catch { setError("Invalid code — please try again"); }
    finally { setLoading(false); }
  };

  const handleDisable = async () => {
    setLoading(true); setError("");
    try {
      await authExtendedApi.disableMFA(disablePassword, disableCode);
      setDisableOpen(false);
      window.location.reload();
    } catch (err: any) {
      setError(err?.response?.data?.detail?.message ?? "Failed to disable MFA");
    } finally { setLoading(false); }
  };

  return (
    <>
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-base">
            <QrCode className="h-4 w-4 text-brand-gold" />
            Two-Factor Authentication
            {mfaEnabled && <Badge variant="success" className="ml-1 text-2xs">Active</Badge>}
          </CardTitle>
          <CardDescription>
            Add an extra layer of security with an authenticator app like Google Authenticator or Authy.
          </CardDescription>
        </CardHeader>
        <CardContent className="flex items-start justify-between gap-4 flex-wrap">
          <div className="space-y-1">
            {mfaEnabled ? (
              <p className="text-sm text-emerald-400 flex items-center gap-1.5">
                <CheckCircle className="h-3.5 w-3.5" /> MFA is active on this account
              </p>
            ) : (
              <p className="text-sm text-muted-foreground/70">
                Your account is not protected by two-factor authentication.
              </p>
            )}
          </div>
          {mfaEnabled ? (
            <Button variant="ghost-gold" size="sm" onClick={() => setDisableOpen(true)}>
              Disable MFA
            </Button>
          ) : (
            <Button variant="gold" size="sm" loading={loading} onClick={startSetup}>
              Enable MFA
            </Button>
          )}
          {error && <p className="w-full text-sm text-destructive">{error}</p>}
        </CardContent>
      </Card>

      {/* Setup dialog */}
      <Dialog open={setupOpen} onOpenChange={setSetupOpen}>
        <DialogContent className="max-w-sm">
          <DialogHeader>
            <DialogTitle>Set up Two-Factor Authentication</DialogTitle>
            <DialogDescription>
              {step === "qr" ? "Scan the QR code with your authenticator app, then enter the 6-digit code." : "Save these backup codes in a safe place. Each can only be used once."}
            </DialogDescription>
          </DialogHeader>
          {step === "qr" && qrData && (
            <div className="space-y-5">
              <div className="flex justify-center">
                <div className="rounded-xl border border-white/10 bg-white p-3">
                  <img src={qrData.qr_code_url} alt="MFA QR code" className="h-44 w-44" />
                </div>
              </div>
              <div className="rounded-xl bg-white/[0.03] border border-white/[0.08] px-3 py-2">
                <p className="text-2xs text-muted-foreground/50 mb-1">Manual entry key</p>
                <p className="font-mono text-xs text-brand-gold break-all">{qrData.secret}</p>
              </div>
              <Input label="Authenticator code" type="text" inputMode="numeric" maxLength={6}
                value={confirmCode} onChange={e => setConfirmCode(e.target.value)} placeholder="000000" />
              {error && <p className="text-sm text-destructive">{error}</p>}
              <Button variant="gold" className="w-full" loading={loading} onClick={confirmSetup}>
                Verify & Activate
              </Button>
            </div>
          )}
          {step === "backup" && qrData && (
            <div className="space-y-4">
              <div className="grid grid-cols-2 gap-2">
                {qrData.backup_codes.map((code) => (
                  <div key={code} className="rounded-lg bg-white/[0.03] border border-white/[0.06] px-3 py-1.5 font-mono text-xs text-center text-foreground/80">
                    {code}
                  </div>
                ))}
              </div>
              <Button variant="gold" className="w-full" onClick={() => { setSetupOpen(false); window.location.reload(); }}>
                Done — I've saved these codes
              </Button>
            </div>
          )}
        </DialogContent>
      </Dialog>

      {/* Disable dialog */}
      <Dialog open={disableOpen} onOpenChange={setDisableOpen}>
        <DialogContent className="max-w-sm">
          <DialogHeader>
            <DialogTitle>Disable Two-Factor Authentication</DialogTitle>
            <DialogDescription>Enter your password and current authenticator code to confirm.</DialogDescription>
          </DialogHeader>
          <div className="space-y-4 mt-2">
            <Input label="Password" type="password" value={disablePassword} onChange={e => setDisablePassword(e.target.value)} />
            <Input label="Authenticator code" type="text" inputMode="numeric" maxLength={6}
              value={disableCode} onChange={e => setDisableCode(e.target.value)} placeholder="000000" />
            {error && <p className="text-sm text-destructive">{error}</p>}
            <div className="flex gap-3">
              <Button variant="ghost" className="flex-1" onClick={() => setDisableOpen(false)}>Cancel</Button>
              <Button variant="destructive" className="flex-1" loading={loading} onClick={handleDisable}>Disable</Button>
            </div>
          </div>
        </DialogContent>
      </Dialog>
    </>
  );
}

// ── Session Card ──────────────────────────────────────────────────────────────
function SessionItem({ session, onRevoke, isRevoking }: {
  session: UserSession; onRevoke: (id: string) => void; isRevoking: boolean;
}) {
  return (
    <div className="flex items-start justify-between gap-4 p-4 rounded-xl border border-white/[0.06] hover:border-white/[0.1] transition-colors">
      <div className="flex items-start gap-3">
        <div className={`mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-lg ${session.is_current ? "bg-brand-gold/10 text-brand-gold" : "bg-white/[0.04] text-muted-foreground/60"}`}>
          <DeviceIcon type={session.device_type} />
        </div>
        <div className="space-y-1">
          <div className="flex items-center gap-2 flex-wrap">
            <span className="text-sm font-medium text-foreground">{session.device_name ?? session.device_type ?? "Unknown device"}</span>
            {session.is_current && <Badge variant="gold" className="text-2xs">Current</Badge>}
          </div>
          <div className="flex items-center gap-3 text-2xs text-muted-foreground/50">
            {session.ip_address && (
              <span className="flex items-center gap-1"><MapPin className="h-3 w-3" />{session.ip_address}</span>
            )}
            <span className="flex items-center gap-1">
              <Clock className="h-3 w-3" />{timeAgo(session.last_active_at)}
            </span>
          </div>
        </div>
      </div>
      {!session.is_current && (
        <Button variant="ghost" size="sm" className="shrink-0 text-destructive hover:text-destructive hover:bg-destructive/10"
          loading={isRevoking} onClick={() => onRevoke(String(session.id))}>
          <Trash2 className="h-3.5 w-3.5" />
        </Button>
      )}
    </div>
  );
}

function SessionsCard() {
  const { sessions, isLoading, revokeOne, revokeOthers, isRevoking } = useSessions();

  return (
    <Card>
      <CardHeader className="flex flex-row items-start justify-between gap-4">
        <div>
          <CardTitle className="flex items-center gap-2 text-base">
            <Lock className="h-4 w-4 text-brand-gold" /> Active Sessions
          </CardTitle>
          <CardDescription className="mt-1">
            {sessions.length} active session{sessions.length !== 1 ? "s" : ""} — manage where you're logged in
          </CardDescription>
        </div>
        {sessions.length > 1 && (
          <Button variant="ghost-gold" size="sm" loading={isRevoking} onClick={() => revokeOthers()}>
            <LogOut className="h-3.5 w-3.5" /> Revoke others
          </Button>
        )}
      </CardHeader>
      <CardContent className="space-y-2">
        {isLoading ? (
          Array.from({ length: 3 }).map((_, i) => (
            <div key={i} className="h-[68px] rounded-xl skeleton" />
          ))
        ) : sessions.length === 0 ? (
          <p className="py-6 text-center text-sm text-muted-foreground/50">No active sessions found.</p>
        ) : (
          sessions.map((s) => (
            <SessionItem key={String(s.id)} session={s} isRevoking={isRevoking}
              onRevoke={(id) => revokeOne(id)} />
          ))
        )}
      </CardContent>
    </Card>
  );
}

// ── Main Security Page ────────────────────────────────────────────────────────
export default function SecurityPage() {
  const { user } = useAuthStore();

  const { data: securityData } = useQuery({
    queryKey: ["security"],
    queryFn: async () => {
      const { data } = await usersApi.getSecurity();
      return data.data;
    },
  });

  return (
    <div className="max-w-3xl space-y-8">
      {/* Header */}
      <motion.div {...anim(0)}>
        <h1 className="font-display text-display-md font-light tracking-tightest">
          Security
        </h1>
        <p className="mt-1.5 text-muted-foreground">Manage your password, two-factor authentication, and active sessions.</p>
      </motion.div>

      {/* Security overview */}
      {securityData && (
        <motion.div {...anim(1)}>
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
            {[
              { label: "Status", value: securityData.is_verified ? "Verified" : "Unverified",
                color: securityData.is_verified ? "text-emerald-400" : "text-amber-400" },
              { label: "MFA",    value: securityData.mfa_enabled ? "Enabled" : "Disabled",
                color: securityData.mfa_enabled ? "text-emerald-400" : "text-muted-foreground" },
              { label: "Sessions", value: String(securityData.active_sessions_count), color: "text-foreground" },
              { label: "Last login", value: securityData.last_login_at
                  ? new Date(securityData.last_login_at).toLocaleDateString() : "—",
                color: "text-foreground" },
            ].map((item) => (
              <div key={item.label} className="rounded-xl border border-white/[0.06] bg-white/[0.02] p-4">
                <p className="text-2xs text-muted-foreground/50 uppercase tracking-wider mb-1.5">{item.label}</p>
                <p className={`text-sm font-medium ${item.color}`}>{item.value}</p>
              </div>
            ))}
          </div>
        </motion.div>
      )}

      {/* Email verification banner */}
      {user && !user.is_verified && (
        <motion.div {...anim(2)}>
          <div className="flex items-start gap-3 rounded-xl border border-amber-500/20 bg-amber-500/5 px-4 py-3">
            <AlertTriangle className="h-4 w-4 text-amber-400 mt-0.5 shrink-0" />
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium text-amber-400">Email not verified</p>
              <p className="text-xs text-muted-foreground/60 mt-0.5">
                Please verify <strong>{user.email}</strong> to secure your account.
              </p>
            </div>
          </div>
        </motion.div>
      )}

      <motion.div {...anim(3)}><PasswordCard /></motion.div>
      <motion.div {...anim(4)}><MFACard /></motion.div>
      <motion.div {...anim(5)}><SessionsCard /></motion.div>

      {/* Danger zone */}
      <motion.div {...anim(6)}>
        <Card className="border-destructive/20">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-base text-destructive">
              <AlertTriangle className="h-4 w-4" /> Danger Zone
            </CardTitle>
            <CardDescription>Irreversible actions — proceed with caution.</CardDescription>
          </CardHeader>
          <CardContent className="flex items-center justify-between gap-4 flex-wrap">
            <div>
              <p className="text-sm font-medium text-foreground">Delete account</p>
              <p className="text-xs text-muted-foreground/60 mt-0.5">Permanently delete your account and all associated data.</p>
            </div>
            <Button variant="outline" size="sm" className="border-destructive/30 text-destructive hover:bg-destructive/10 hover:border-destructive/50">
              Delete Account
            </Button>
          </CardContent>
        </Card>
      </motion.div>
    </div>
  );
}
