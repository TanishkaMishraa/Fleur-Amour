"use client";
/**
 * AuraFit — EmailVerificationBanner.
 * Shown in dashboard when user's email is unverified.
 * Allows resending the verification email with rate-limit feedback.
 */
import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Mail, X, CheckCircle, AlertTriangle } from "lucide-react";
import { Button } from "@/components/ui/button";
import { useAuthStore } from "@/lib/stores/auth.store";
import { authExtendedApi } from "@/lib/api/users";

export function EmailVerificationBanner() {
  const { user } = useAuthStore();
  const [dismissed, setDismissed] = useState(false);
  const [sending,   setSending]   = useState(false);
  const [sent,      setSent]      = useState(false);
  const [error,     setError]     = useState("");

  // Only show when authenticated and email not verified
  if (!user || user.is_verified || dismissed) return null;

  const handleResend = async () => {
    setSending(true);
    setError("");
    try {
      await authExtendedApi.resendVerification(user.email);
      setSent(true);
    } catch (err: any) {
      const msg = err?.response?.data?.errors?.[0]?.message;
      setError(msg === "RATE_LIMITED" ? "Please wait 2 minutes before resending." : "Failed to send. Please try again.");
    } finally {
      setSending(false);
    }
  };

  return (
    <AnimatePresence>
      <motion.div
        initial={{ opacity: 0, y: -16, height: 0 }}
        animate={{ opacity: 1, y: 0, height: "auto" }}
        exit={{ opacity: 0, y: -16, height: 0 }}
        transition={{ duration: 0.35, ease: [0.23, 1, 0.32, 1] }}
        className="mb-6 overflow-hidden"
      >
        <div className="flex items-center gap-3 rounded-2xl border border-amber-500/20 bg-amber-500/[0.06] px-4 py-3">
          <AlertTriangle className="h-4 w-4 shrink-0 text-amber-400" />

          <div className="flex-1 min-w-0">
            {sent ? (
              <div className="flex items-center gap-2">
                <CheckCircle className="h-4 w-4 text-emerald-400 shrink-0" />
                <p className="text-sm text-foreground/80">
                  Verification email sent to <strong>{user.email}</strong>. Check your inbox.
                </p>
              </div>
            ) : (
              <p className="text-sm text-foreground/70">
                <strong className="text-foreground">Verify your email</strong> — check your inbox for a link from AuraFit.{" "}
                {error && <span className="text-amber-400">{error}</span>}
              </p>
            )}
          </div>

          {!sent && (
            <Button
              variant="ghost"
              size="sm"
              loading={sending}
              onClick={handleResend}
              className="shrink-0 text-xs text-amber-400 hover:text-amber-300 hover:bg-amber-400/10"
            >
              <Mail className="h-3.5 w-3.5 mr-1" /> Resend
            </Button>
          )}

          <button
            onClick={() => setDismissed(true)}
            className="shrink-0 p-1 rounded-lg text-foreground/30 hover:text-foreground transition-colors"
            aria-label="Dismiss"
          >
            <X className="h-4 w-4" />
          </button>
        </div>
      </motion.div>
    </AnimatePresence>
  );
}
