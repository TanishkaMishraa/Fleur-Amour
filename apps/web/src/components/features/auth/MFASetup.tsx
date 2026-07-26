"use client";
import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Shield, Copy, Check, AlertTriangle } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { authExtendedApi } from "@/lib/api/users";
import { useAuthStore } from "@/lib/stores/auth.store";

type Step = "intro" | "qr" | "verify" | "done";

interface MFASetupData {
  secret:       string;
  qr_code_url:  string;
  backup_codes: string[];
}

interface MFASetupProps {
  onComplete: () => void;
  onCancel:   () => void;
}

export function MFASetup({ onComplete, onCancel }: MFASetupProps) {
  const [step, setStep]       = useState<Step>("intro");
  const [data, setData]       = useState<MFASetupData | null>(null);
  const [code, setCode]       = useState("");
  const [error, setError]     = useState("");
  const [loading, setLoading] = useState(false);
  const [copied, setCopied]   = useState(false);
  const { patchUser }         = useAuthStore();

  const startSetup = async () => {
    setLoading(true);
    try {
      const res = await authExtendedApi.setupMFA();
      if (res.data.success && res.data.data) {
        setData(res.data.data);
        setStep("qr");
      }
    } catch { setError("Failed to start MFA setup. Try again."); }
    finally { setLoading(false); }
  };

  const confirm = async () => {
    if (code.length !== 6) { setError("Enter the 6-digit code from your app."); return; }
    setLoading(true); setError("");
    try {
      await authExtendedApi.confirmMFA(code);
      patchUser({ mfa_enabled: true });
      setStep("done");
    } catch { setError("Code incorrect. Try again."); }
    finally { setLoading(false); }
  };

  const copySecret = () => {
    if (data?.secret) {
      navigator.clipboard.writeText(data.secret);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  return (
    <AnimatePresence mode="wait">
      {step === "intro" && (
        <motion.div key="intro" initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -12 }}
          className="space-y-6">
          <div className="flex h-14 w-14 items-center justify-center rounded-2xl bg-brand-gold/10 border border-brand-gold/20">
            <Shield className="h-7 w-7 text-brand-gold" />
          </div>
          <div>
            <h3 className="font-display text-display-sm font-light">Enable two-factor authentication</h3>
            <p className="mt-2 text-sm text-muted-foreground leading-relaxed">
              Add an extra layer of security. You'll need an authenticator app like Google Authenticator or Authy.
            </p>
          </div>
          {error && <ErrorBox message={error} />}
          <div className="flex gap-3">
            <Button variant="ghost-gold" onClick={onCancel} className="flex-1">Cancel</Button>
            <Button variant="gold" onClick={startSetup} loading={loading} className="flex-1">
              Get Started
            </Button>
          </div>
        </motion.div>
      )}

      {step === "qr" && data && (
        <motion.div key="qr" initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -12 }}
          className="space-y-6">
          <div>
            <h3 className="font-display text-display-sm font-light">Scan QR code</h3>
            <p className="mt-1.5 text-sm text-muted-foreground">
              Open your authenticator app and scan this code.
            </p>
          </div>
          {/* QR Code */}
          <div className="flex justify-center">
            <div className="p-4 rounded-2xl bg-white shadow-luxury">
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img src={data.qr_code_url} alt="MFA QR Code" className="h-48 w-48" />
            </div>
          </div>
          {/* Manual entry */}
          <div className="rounded-xl border border-white/[0.06] bg-white/[0.02] p-4 space-y-2">
            <p className="text-xs text-muted-foreground/60 uppercase tracking-widest">Manual entry key</p>
            <div className="flex items-center gap-2">
              <code className="flex-1 text-xs font-mono text-brand-gold break-all">{data.secret}</code>
              <button onClick={copySecret} className="p-1.5 rounded-lg hover:bg-white/5 transition-colors text-muted-foreground/50 hover:text-foreground">
                {copied ? <Check className="h-3.5 w-3.5 text-emerald-400" /> : <Copy className="h-3.5 w-3.5" />}
              </button>
            </div>
          </div>
          <Button variant="gold" onClick={() => setStep("verify")} className="w-full">
            I've scanned it — Next
          </Button>
        </motion.div>
      )}

      {step === "verify" && data && (
        <motion.div key="verify" initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -12 }}
          className="space-y-6">
          <div>
            <h3 className="font-display text-display-sm font-light">Verify your code</h3>
            <p className="mt-1.5 text-sm text-muted-foreground">Enter the 6-digit code from your app to confirm.</p>
          </div>
          <Input
            label="Authenticator code"
            type="text"
            inputMode="numeric"
            maxLength={6}
            value={code}
            onChange={(e) => setCode(e.target.value.replace(/\D/g, ""))}
            placeholder="000000"
            className="text-center text-xl tracking-[0.5em] font-mono"
            autoFocus
          />
          {error && <ErrorBox message={error} />}
          {/* Backup codes preview */}
          <details className="group">
            <summary className="cursor-pointer text-xs text-muted-foreground/60 hover:text-muted-foreground transition-colors list-none flex items-center gap-1">
              <span>Save your backup codes</span>
              <span className="text-2xs group-open:rotate-90 transition-transform">›</span>
            </summary>
            <div className="mt-3 grid grid-cols-2 gap-2">
              {data.backup_codes.map((c) => (
                <code key={c} className="rounded-lg border border-white/[0.06] bg-white/[0.02] px-3 py-1.5 text-xs font-mono text-center text-foreground/60">
                  {c}
                </code>
              ))}
            </div>
            <p className="mt-2 text-2xs text-muted-foreground/40">Store these securely. Each is single-use.</p>
          </details>
          <div className="flex gap-3">
            <Button variant="ghost-gold" onClick={() => setStep("qr")} className="flex-1">Back</Button>
            <Button variant="gold" onClick={confirm} loading={loading} className="flex-1">
              Confirm
            </Button>
          </div>
        </motion.div>
      )}

      {step === "done" && (
        <motion.div key="done" initial={{ opacity: 0, scale: 0.95 }} animate={{ opacity: 1, scale: 1 }}
          className="space-y-6 text-center py-4">
          <div className="mx-auto flex h-14 w-14 items-center justify-center rounded-full bg-emerald-500/15 border border-emerald-500/25">
            <Check className="h-7 w-7 text-emerald-400" />
          </div>
          <div>
            <h3 className="font-display text-display-sm font-light">Two-factor enabled</h3>
            <p className="mt-2 text-sm text-muted-foreground">Your account is now protected with 2FA.</p>
          </div>
          <Button variant="gold" onClick={onComplete} className="w-full">Done</Button>
        </motion.div>
      )}
    </AnimatePresence>
  );
}

function ErrorBox({ message }: { message: string }) {
  return (
    <div className="flex items-center gap-2 rounded-xl border border-destructive/30 bg-destructive/10 px-4 py-3 text-sm text-destructive">
      <AlertTriangle className="h-4 w-4 shrink-0" />
      {message}
    </div>
  );
}
