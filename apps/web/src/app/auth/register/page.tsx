"use client";
import { useState } from "react";
import Link from "next/link";
import { motion } from "framer-motion";
import { Eye, EyeOff, Sparkles, ArrowRight, Check, Mail } from "lucide-react";
import { useAuth } from "@/lib/hooks/useAuth";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { OAuthButtons } from "@/components/features/auth/OAuthButtons";
import { GoldDivider } from "@/components/shared/GoldDivider";

const PW_RULES = [
  { label: "8+ characters",  test: (p: string) => p.length >= 8 },
  { label: "One uppercase",  test: (p: string) => /[A-Z]/.test(p) },
  { label: "One number",     test: (p: string) => /\d/.test(p) },
];

export default function RegisterPage() {
  const { register, isLoading } = useAuth();
  const [form, setForm]  = useState({ full_name: "", email: "", password: "" });
  const [showPw, setShowPw] = useState(false);
  const [error, setError]   = useState("");
  const [done, setDone]     = useState(false);
  const set = (k: keyof typeof form) => (e: React.ChangeEvent<HTMLInputElement>) =>
    setForm((f) => ({ ...f, [k]: e.target.value }));

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault(); setError("");
    const result = await register(form);
    if (result.success) setDone(true);
    else setError(result.error ?? "Registration failed");
  };

  if (done) return (
    <div className="flex min-h-screen items-center justify-center bg-brand-black noise">
      <motion.div initial={{ opacity: 0, scale: 0.9 }} animate={{ opacity: 1, scale: 1 }}
        className="luxury-card p-10 text-center space-y-5 max-w-sm w-full mx-6">
        <div className="mx-auto flex h-16 w-16 items-center justify-center rounded-2xl bg-emerald-500/10 border border-emerald-500/20">
          <Mail className="h-8 w-8 text-emerald-400" />
        </div>
        <div>
          <h2 className="font-display text-display-sm font-light">Check your email</h2>
          <p className="mt-2 text-sm text-muted-foreground">
            We sent a verification link to <strong className="text-foreground">{form.email}</strong>.
            Click it to activate your account.
          </p>
        </div>
        <Button variant="gold" className="w-full" asChild>
          <Link href="/auth/login">Sign In <ArrowRight className="h-4 w-4" /></Link>
        </Button>
        <p className="text-xs text-muted-foreground/40">
          Didn't get it?{" "}
          <Link href="/auth/login" className="underline hover:text-muted-foreground">Check spam</Link>
        </p>
      </motion.div>
    </div>
  );

  return (
    <div className="relative flex min-h-screen items-center justify-center bg-brand-black noise py-12">
      <div className="pointer-events-none absolute inset-0">
        <div className="absolute top-0 left-1/2 -translate-x-1/2 h-[500px] w-[500px] rounded-full bg-brand-gold/[0.06] blur-[120px]" />
      </div>

      <div className="relative z-10 w-full max-w-md px-6">
        <motion.div initial={{ opacity: 0, y: -20 }} animate={{ opacity: 1, y: 0 }}
          className="mb-10 flex justify-center">
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
          transition={{ delay: 0.1 }} className="luxury-card p-8 space-y-6">
          <div className="space-y-1">
            <h1 className="font-display text-display-sm font-light">Begin your journey</h1>
            <p className="text-sm text-muted-foreground">Create your free AuraFit account</p>
          </div>

          <OAuthButtons mode="register" />
          <GoldDivider />

          {error && (
            <div className="rounded-xl border border-destructive/30 bg-destructive/10 px-4 py-3 text-sm text-destructive">
              {error}
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-4">
            <Input label="Full name" type="text" value={form.full_name} onChange={set("full_name")}
              placeholder="Your name" autoComplete="name" required />
            <Input label="Email" type="email" value={form.email} onChange={set("email")}
              placeholder="you@example.com" autoComplete="email" required />

            <div className="relative">
              <Input label="Password" type={showPw ? "text" : "password"}
                value={form.password} onChange={set("password")}
                placeholder="Create a strong password" autoComplete="new-password" required />
              <button type="button" onClick={() => setShowPw(!showPw)}
                className="absolute right-3 top-8 text-muted-foreground/40 hover:text-muted-foreground transition-colors">
                {showPw ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
              </button>
            </div>

            {form.password && (
              <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }}
                className="flex gap-4 flex-wrap">
                {PW_RULES.map((rule) => {
                  const ok = rule.test(form.password);
                  return (
                    <span key={rule.label}
                      className={`flex items-center gap-1.5 text-xs transition-colors ${ok ? "text-emerald-400" : "text-muted-foreground/40"}`}>
                      <div className={`h-1.5 w-1.5 rounded-full transition-colors ${ok ? "bg-emerald-400" : "bg-white/10"}`} />
                      {rule.label}
                    </span>
                  );
                })}
              </motion.div>
            )}

            <Button type="submit" variant="gold" className="w-full" loading={isLoading}>
              Create Account <ArrowRight className="h-4 w-4" />
            </Button>
          </form>

          <p className="text-center text-sm text-muted-foreground">
            Already have an account?{" "}
            <Link href="/auth/login"
              className="text-brand-gold hover:text-brand-gold-light font-medium transition-colors">
              Sign in
            </Link>
          </p>
        </motion.div>

        <p className="mt-6 text-center text-xs text-muted-foreground/30">
          By creating an account you agree to our{" "}
          <Link href="/terms" className="underline hover:text-muted-foreground/60">Terms</Link>
          {" "}and{" "}
          <Link href="/privacy" className="underline hover:text-muted-foreground/60">Privacy Policy</Link>
        </p>
      </div>
    </div>
  );
}
