"use client";
import { useState } from "react";
import Link from "next/link";
import { motion } from "framer-motion";
import { Eye, EyeOff, Sparkles, ArrowRight } from "lucide-react";
import { useAuth } from "@/lib/hooks/useAuth";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { OAuthButtons } from "@/components/features/auth/OAuthButtons";
import { GoldDivider } from "@/components/shared/GoldDivider";

export default function LoginPage() {
  const { login, isLoading } = useAuth();
  const [email, setEmail]     = useState("");
  const [password, setPw]     = useState("");
  const [mfaCode, setMfa]     = useState("");
  const [showPw, setShowPw]   = useState(false);
  const [needsMfa, setNeedsMfa] = useState(false);
  const [error, setError]     = useState("");

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    const result = await login(email, password, needsMfa ? mfaCode : undefined);
    if (!result.success) {
      if (result.code === "MFA_REQUIRED") {
        setNeedsMfa(true);
        setError("Enter your authenticator code below.");
      } else {
        setError(result.error ?? "Login failed");
      }
    }
  };

  return (
    <div className="relative flex min-h-screen items-center justify-center bg-brand-black noise py-12">
      <div className="pointer-events-none absolute inset-0 overflow-hidden">
        <div className="absolute top-0 left-1/2 -translate-x-1/2 h-[500px] w-[500px] rounded-full bg-brand-gold/[0.06] blur-[120px]" />
        <div className="absolute bottom-0 right-0 h-[300px] w-[300px] rounded-full bg-brand-rose/[0.04] blur-[80px]" />
      </div>

      <div className="relative z-10 w-full max-w-md px-6">
        <motion.div initial={{ opacity: 0, y: -20 }} animate={{ opacity: 1, y: 0 }}
          className="mb-10 flex flex-col items-center gap-3">
          <Link href="/" className="flex items-center gap-2.5 group">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-gold-gradient shadow-gold-sm transition-transform group-hover:scale-105">
              <Sparkles className="h-5 w-5 text-brand-black" />
            </div>
            <span className="font-display text-2xl font-medium">
              Aura<span className="text-gold-gradient">Fit</span>
            </span>
          </Link>
        </motion.div>

        <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1 }} className="luxury-card p-8 space-y-7">
          <div className="space-y-1">
            <h1 className="font-display text-display-sm font-light">Welcome back</h1>
            <p className="text-sm text-muted-foreground">Sign in to your AuraFit account</p>
          </div>

          {/* OAuth */}
          <OAuthButtons mode="login" />

          <GoldDivider />

          {/* Error */}
          {error && (
            <motion.div initial={{ opacity: 0, scale: 0.96 }} animate={{ opacity: 1, scale: 1 }}
              className="rounded-xl border border-destructive/30 bg-destructive/10 px-4 py-3 text-sm text-destructive">
              {error}
            </motion.div>
          )}

          <form onSubmit={handleSubmit} className="space-y-4">
            <Input label="Email address" type="email" value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="you@example.com" autoComplete="email" required />

            <div className="relative">
              <Input label="Password" type={showPw ? "text" : "password"}
                value={password} onChange={(e) => setPw(e.target.value)}
                placeholder="••••••••" autoComplete="current-password" required />
              <button type="button" onClick={() => setShowPw(!showPw)}
                className="absolute right-3 top-8 text-muted-foreground/40 hover:text-muted-foreground transition-colors">
                {showPw ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
              </button>
            </div>

            {needsMfa && (
              <motion.div initial={{ opacity: 0, height: 0 }} animate={{ opacity: 1, height: "auto" }}>
                <Input label="Authenticator code" type="text" inputMode="numeric"
                  maxLength={6} value={mfaCode}
                  onChange={(e) => setMfa(e.target.value.replace(/\D/g, ""))}
                  placeholder="000000"
                  className="text-center tracking-[0.5em] font-mono" autoFocus />
              </motion.div>
            )}

            <div className="flex justify-end">
              <Link href="/auth/forgot-password"
                className="text-xs text-brand-gold/70 hover:text-brand-gold transition-colors">
                Forgot password?
              </Link>
            </div>

            <Button type="submit" variant="gold" className="w-full" loading={isLoading}>
              Sign In <ArrowRight className="h-4 w-4" />
            </Button>
          </form>

          <p className="text-center text-sm text-muted-foreground">
            No account?{" "}
            <Link href="/auth/register"
              className="text-brand-gold hover:text-brand-gold-light font-medium transition-colors">
              Create one free
            </Link>
          </p>
        </motion.div>

        <p className="mt-6 text-center text-xs text-muted-foreground/30">
          Protected by RS256 JWT · Argon2id · AuraFit Security
        </p>
      </div>
    </div>
  );
}
