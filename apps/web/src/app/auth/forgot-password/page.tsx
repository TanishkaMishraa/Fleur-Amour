"use client";
import { useState } from "react";
import Link from "next/link";
import { motion } from "framer-motion";
import { ArrowLeft, Mail, Sparkles } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { authApi } from "@/lib/api/auth";

export default function ForgotPasswordPage() {
  const [email, setEmail]       = useState("");
  const [sent, setSent]         = useState(false);
  const [loading, setLoading]   = useState(false);
  const [error, setError]       = useState("");

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError("");
    try {
      await authApi.forgotPassword(email);
      setSent(true);
    } catch {
      setError("Unable to send reset email. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="relative flex min-h-screen items-center justify-center bg-brand-black noise">
      <div className="pointer-events-none absolute inset-0">
        <div className="absolute top-0 left-1/2 -translate-x-1/2 h-96 w-96 rounded-full bg-brand-gold/[0.06] blur-[100px]" />
      </div>

      <div className="relative z-10 w-full max-w-md px-6">
        <motion.div initial={{ opacity: 0, y: -20 }} animate={{ opacity: 1, y: 0 }}
          className="mb-10 flex flex-col items-center gap-3">
          <Link href="/" className="flex items-center gap-2.5">
            <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-gold-gradient shadow-gold-sm">
              <Sparkles className="h-4 w-4 text-brand-black" />
            </div>
            <span className="font-display text-2xl font-medium">
              Aura<span className="text-gold-gradient">Fit</span>
            </span>
          </Link>
        </motion.div>

        <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1 }} className="luxury-card p-8 space-y-7">
          {sent ? (
            <div className="text-center space-y-4 py-4">
              <div className="mx-auto h-14 w-14 rounded-2xl bg-brand-gold/10 border border-brand-gold/20 flex items-center justify-center">
                <Mail className="h-6 w-6 text-brand-gold" />
              </div>
              <h1 className="font-display text-display-sm font-light">Check your inbox</h1>
              <p className="text-sm text-muted-foreground">
                We've sent a password reset link to <strong className="text-foreground">{email}</strong>.
              </p>
              <Button variant="ghost-gold" asChild className="w-full mt-4">
                <Link href="/auth/login"><ArrowLeft className="h-4 w-4" /> Back to Sign In</Link>
              </Button>
            </div>
          ) : (
            <>
              <div>
                <h1 className="font-display text-display-sm font-light">Reset password</h1>
                <p className="mt-1.5 text-sm text-muted-foreground">Enter your email and we'll send a reset link.</p>
              </div>

              {error && (
                <div className="rounded-xl border border-destructive/30 bg-destructive/10 px-4 py-3 text-sm text-destructive">{error}</div>
              )}

              <form onSubmit={handleSubmit} className="space-y-4">
                <Input label="Email address" type="email" value={email}
                  onChange={(e) => setEmail(e.target.value)} placeholder="you@example.com" required />
                <Button type="submit" variant="gold" className="w-full" loading={loading}>
                  <Mail className="h-4 w-4" /> Send Reset Link
                </Button>
              </form>

              <Button variant="ghost" size="sm" asChild className="w-full">
                <Link href="/auth/login"><ArrowLeft className="h-4 w-4" /> Back to Sign In</Link>
              </Button>
            </>
          )}
        </motion.div>
      </div>
    </div>
  );
}
