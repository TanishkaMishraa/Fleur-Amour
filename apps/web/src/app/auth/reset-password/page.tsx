"use client";
import { useState } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import Link from "next/link";
import { motion } from "framer-motion";
import { Eye, EyeOff, Sparkles, Lock, Check } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { authApi } from "@/lib/api/auth";

const PW_RULES = [
  { label: "8+ characters", test: (p: string) => p.length >= 8 },
  { label: "One uppercase",  test: (p: string) => /[A-Z]/.test(p) },
  { label: "One number",    test: (p: string) => /\d/.test(p) },
];

export default function ResetPasswordPage() {
  const params    = useSearchParams();
  const router    = useRouter();
  const token     = params.get("token") ?? "";
  const [pw, setPw]         = useState("");
  const [confirm, setConfirm] = useState("");
  const [showPw, setShowPw] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError]   = useState("");
  const [done, setDone]     = useState(false);

  const allRulesMet = PW_RULES.every((r) => r.test(pw));

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault(); setError("");
    if (!allRulesMet) { setError("Password doesn't meet requirements."); return; }
    if (pw !== confirm) { setError("Passwords do not match."); return; }
    setLoading(true);
    try {
      await authApi.resetPassword(token, pw);
      setDone(true);
      setTimeout(() => router.push("/auth/login"), 3000);
    } catch (err: any) {
      setError(err?.response?.data?.errors?.[0]?.message ?? "Reset failed. Link may be expired.");
    } finally { setLoading(false); }
  };

  return (
    <div className="flex min-h-screen items-center justify-center bg-brand-black noise px-6">
      <div className="pointer-events-none absolute inset-0">
        <div className="absolute top-0 left-1/2 -translate-x-1/2 h-96 w-96 rounded-full bg-brand-gold/[0.06] blur-[100px]" />
      </div>

      <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }}
        className="relative z-10 w-full max-w-md">
        <div className="mb-10 flex justify-center">
          <Link href="/" className="flex items-center gap-2.5">
            <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-gold-gradient shadow-gold-sm">
              <Sparkles className="h-4 w-4 text-brand-black" />
            </div>
            <span className="font-display text-2xl font-medium">
              Aura<span className="text-gold-gradient">Fit</span>
            </span>
          </Link>
        </div>

        <div className="luxury-card p-8 space-y-7">
          {done ? (
            <div className="text-center space-y-5 py-4">
              <div className="mx-auto flex h-14 w-14 items-center justify-center rounded-2xl bg-emerald-500/10 border border-emerald-500/20">
                <Check className="h-7 w-7 text-emerald-400" />
              </div>
              <h1 className="font-display text-display-sm font-light">Password updated</h1>
              <p className="text-sm text-muted-foreground">
                All sessions have been signed out. Redirecting to sign in…
              </p>
            </div>
          ) : (
            <>
              <div className="space-y-1">
                <div className="flex items-center gap-2">
                  <Lock className="h-5 w-5 text-brand-gold/70" />
                  <h1 className="font-display text-display-sm font-light">Set new password</h1>
                </div>
                <p className="text-sm text-muted-foreground">Choose a strong password for your account.</p>
              </div>

              {error && (
                <div className="rounded-xl border border-destructive/30 bg-destructive/10 px-4 py-3 text-sm text-destructive">
                  {error}
                </div>
              )}

              <form onSubmit={handleSubmit} className="space-y-4">
                <div className="relative">
                  <Input label="New password" type={showPw ? "text" : "password"}
                    value={pw} onChange={(e) => setPw(e.target.value)}
                    placeholder="Create a strong password" autoComplete="new-password" required />
                  <button type="button" onClick={() => setShowPw(!showPw)}
                    className="absolute right-3 top-8 text-muted-foreground/40 hover:text-muted-foreground transition-colors">
                    {showPw ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                  </button>
                </div>

                {pw && (
                  <div className="flex flex-wrap gap-3">
                    {PW_RULES.map((rule) => {
                      const ok = rule.test(pw);
                      return (
                        <span key={rule.label}
                          className={`flex items-center gap-1 text-xs transition-colors ${ok ? "text-emerald-400" : "text-muted-foreground/40"}`}>
                          <div className={`h-1.5 w-1.5 rounded-full ${ok ? "bg-emerald-400" : "bg-white/10"}`} />
                          {rule.label}
                        </span>
                      );
                    })}
                  </div>
                )}

                <Input label="Confirm password" type="password"
                  value={confirm} onChange={(e) => setConfirm(e.target.value)}
                  placeholder="Repeat your password" autoComplete="new-password"
                  error={confirm && pw !== confirm ? "Passwords do not match" : undefined} required />

                <Button type="submit" variant="gold" className="w-full" loading={loading}>
                  <Lock className="h-4 w-4" /> Update Password
                </Button>
              </form>

              <p className="text-center text-sm">
                <Link href="/auth/login"
                  className="text-muted-foreground hover:text-foreground transition-colors">
                  Back to sign in
                </Link>
              </p>
            </>
          )}
        </div>
      </motion.div>
    </div>
  );
}
