"use client";
import { useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import Link from "next/link";
import { motion } from "framer-motion";
import { CheckCircle, XCircle, Sparkles, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { authExtendedApi } from "@/lib/api/users";

type State = "verifying" | "success" | "error";

export default function VerifyEmailPage() {
  const params        = useSearchParams();
  const token         = params.get("token");
  const [state, setState] = useState<State>("verifying");

  useEffect(() => {
    if (!token) { setState("error"); return; }
    authExtendedApi.verifyEmail(token)
      .then(() => setState("success"))
      .catch(() => setState("error"));
  }, [token]);

  return (
    <div className="flex min-h-screen items-center justify-center bg-brand-black noise px-6">
      <div className="pointer-events-none absolute inset-0">
        <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 h-80 w-80 rounded-full bg-brand-gold/[0.06] blur-[80px]" />
      </div>

      <motion.div initial={{ opacity: 0, scale: 0.95 }} animate={{ opacity: 1, scale: 1 }}
        className="luxury-card p-10 max-w-sm w-full text-center space-y-6 relative z-10">

        {/* Logo */}
        <Link href="/" className="inline-flex items-center gap-2">
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-gold-gradient">
            <Sparkles className="h-4 w-4 text-brand-black" />
          </div>
          <span className="font-display text-xl font-medium">
            Aura<span className="text-gold-gradient">Fit</span>
          </span>
        </Link>

        {state === "verifying" && (
          <div className="space-y-4 py-4">
            <Loader2 className="h-12 w-12 text-brand-gold animate-spin mx-auto" />
            <p className="text-muted-foreground">Verifying your email…</p>
          </div>
        )}

        {state === "success" && (
          <div className="space-y-4">
            <div className="mx-auto flex h-16 w-16 items-center justify-center rounded-2xl bg-emerald-500/10 border border-emerald-500/20">
              <CheckCircle className="h-8 w-8 text-emerald-400" />
            </div>
            <h1 className="font-display text-display-sm font-light">Email verified!</h1>
            <p className="text-sm text-muted-foreground">Your account is now active. Sign in to get started.</p>
            <Button variant="gold" className="w-full" asChild>
              <Link href="/auth/login">Sign In</Link>
            </Button>
          </div>
        )}

        {state === "error" && (
          <div className="space-y-4">
            <div className="mx-auto flex h-16 w-16 items-center justify-center rounded-2xl bg-destructive/10 border border-destructive/20">
              <XCircle className="h-8 w-8 text-destructive" />
            </div>
            <h1 className="font-display text-display-sm font-light">Link invalid or expired</h1>
            <p className="text-sm text-muted-foreground">
              Verification links expire after 24 hours. Request a new one.
            </p>
            <Button variant="ghost-gold" className="w-full" asChild>
              <Link href="/auth/login">Back to Sign In</Link>
            </Button>
          </div>
        )}
      </motion.div>
    </div>
  );
}
