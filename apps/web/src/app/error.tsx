"use client";
import { useEffect } from "react";
import { motion } from "framer-motion";
import { AlertTriangle, RefreshCw } from "lucide-react";
import { Button } from "@/components/ui/button";

export default function ErrorPage({ error, reset }: { error: Error & { digest?: string }; reset: () => void }) {
  useEffect(() => { console.error("AuraFit error:", error); }, [error]);
  return (
    <div className="flex min-h-screen items-center justify-center bg-brand-black text-center px-6">
      <motion.div
        initial={{ opacity: 0, scale: 0.95 }} animate={{ opacity: 1, scale: 1 }}
        className="space-y-6 max-w-sm"
      >
        <div className="mx-auto h-14 w-14 rounded-2xl border border-destructive/30 bg-destructive/10 flex items-center justify-center">
          <AlertTriangle className="h-6 w-6 text-destructive" />
        </div>
        <div>
          <h2 className="font-display text-display-sm font-light">Something went wrong</h2>
          <p className="mt-2 text-sm text-muted-foreground">{error.message ?? "An unexpected error occurred."}</p>
        </div>
        <Button variant="gold" onClick={reset}>
          <RefreshCw className="h-4 w-4" /> Try again
        </Button>
      </motion.div>
    </div>
  );
}
