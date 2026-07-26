"use client";
/**
 * AuraFit — OAuth Callback Page.
 * Handles the redirect from Google after OAuth authorisation.
 * Exchanges the `code` query param for tokens via the backend.
 * Route: /auth/callback?code=...&state=...&provider=google
 */
import { useEffect, useState } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import Link from "next/link";
import { motion } from "framer-motion";
import { Sparkles, CheckCircle, XCircle } from "lucide-react";
import { Button } from "@/components/ui/button";
import { authExtendedApi } from "@/lib/api/users";
import { setAccessToken } from "@/lib/api/client";
import { usersApi } from "@/lib/api/users";
import { useAuthStore } from "@/lib/stores/auth.store";

type State = "loading" | "success" | "error";

export default function OAuthCallbackPage() {
  const params  = useSearchParams();
  const router  = useRouter();
  const store   = useAuthStore();
  const [state, setState] = useState<State>("loading");
  const [errMsg, setErrMsg] = useState("");

  useEffect(() => {
    const code     = params.get("code");
    const stateVal = params.get("state") ?? undefined;
    // provider is either in URL param (Apple) or assumed google from the one OAuth flow
    const provider = params.get("provider") ?? "google";
    const error    = params.get("error");

    if (error || !code) {
      setState("error");
      setErrMsg(error === "access_denied" ? "Sign-in was cancelled." : "OAuth failed. Please try again.");
      return;
    }

    (async () => {
      try {
        const { data } = await authExtendedApi.oauthCallback(provider, code, stateVal);
        if (!data.success || !data.data) {
          throw new Error(data.errors?.[0]?.message ?? "OAuth sign-in failed");
        }
        setAccessToken(data.data.access_token);

        // Fetch full user data
        const meRes = await usersApi.getMe();
        if (meRes.data.success && meRes.data.data) {
          store.setUser(meRes.data.data.user);
          store.setProfile(meRes.data.data.profile ?? null);
          store.setPreferences(meRes.data.data.preferences ?? null);
        }
        setState("success");
        setTimeout(() => router.push("/dashboard"), 1200);
      } catch (err: any) {
        setState("error");
        setErrMsg(err?.response?.data?.errors?.[0]?.message ?? err?.message ?? "Sign-in failed");
      }
    })();
  }, [params, router, store]);

  return (
    <div className="flex min-h-screen items-center justify-center bg-brand-black noise px-6">
      <div className="pointer-events-none absolute inset-0">
        <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 h-80 w-80 rounded-full bg-brand-gold/[0.06] blur-[80px]" />
      </div>

      <motion.div
        initial={{ opacity: 0, scale: 0.95 }}
        animate={{ opacity: 1, scale: 1 }}
        className="luxury-card p-10 max-w-sm w-full text-center space-y-6 relative z-10"
      >
        {/* Logo */}
        <Link href="/" className="inline-flex items-center gap-2.5">
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-gold-gradient shadow-gold-sm">
            <Sparkles className="h-4 w-4 text-brand-black" />
          </div>
          <span className="font-display text-xl font-medium">
            Aura<span className="text-gold-gradient">Fit</span>
          </span>
        </Link>

        {state === "loading" && (
          <div className="space-y-5 py-4">
            <div className="relative mx-auto w-fit">
              <div className="h-14 w-14 rounded-2xl bg-gold-gradient flex items-center justify-center shadow-gold-glow animate-float">
                <Sparkles className="h-6 w-6 text-brand-black" />
              </div>
              <div className="absolute -inset-2 rounded-2xl border border-brand-gold/20 animate-spin-slow" />
            </div>
            <div>
              <p className="font-medium text-foreground">Completing sign-in…</p>
              <p className="text-sm text-muted-foreground mt-1">Just a moment</p>
            </div>
          </div>
        )}

        {state === "success" && (
          <div className="space-y-4 py-2">
            <div className="mx-auto flex h-16 w-16 items-center justify-center rounded-2xl bg-emerald-500/10 border border-emerald-500/20">
              <CheckCircle className="h-8 w-8 text-emerald-400" />
            </div>
            <h1 className="font-display text-display-sm font-light">You're in!</h1>
            <p className="text-sm text-muted-foreground">Redirecting to your dashboard…</p>
          </div>
        )}

        {state === "error" && (
          <div className="space-y-5">
            <div className="mx-auto flex h-16 w-16 items-center justify-center rounded-2xl bg-destructive/10 border border-destructive/20">
              <XCircle className="h-8 w-8 text-destructive" />
            </div>
            <div>
              <h1 className="font-display text-display-sm font-light">Sign-in failed</h1>
              <p className="mt-2 text-sm text-muted-foreground">{errMsg}</p>
            </div>
            <div className="flex flex-col gap-2">
              <Button variant="gold" asChild>
                <Link href="/auth/login">Try again</Link>
              </Button>
              <Button variant="ghost" size="sm" asChild>
                <Link href="/">Go home</Link>
              </Button>
            </div>
          </div>
        )}
      </motion.div>
    </div>
  );
}
