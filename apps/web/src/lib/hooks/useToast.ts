/**
 * AuraFit — Toast hook (Radix-based, no external lib).
 * Usage: const { toast } = useToast(); toast({ title: "Done", variant: "success" });
 */
import { useState, useCallback } from "react";

type ToastVariant = "default" | "destructive" | "success";

interface ToastItem {
  id: string;
  title?: string;
  description?: string;
  variant?: ToastVariant;
  action?: React.ReactElement;
  duration?: number;
}

let globalToastFn: ((toast: Omit<ToastItem, "id">) => void) | null = null;

export function useToast() {
  const [toasts, setToasts] = useState<ToastItem[]>([]);

  const toast = useCallback((props: Omit<ToastItem, "id">) => {
    const id = Math.random().toString(36).slice(2);
    setToasts((prev) => [...prev, { ...props, id }]);
    setTimeout(() => {
      setToasts((prev) => prev.filter((t) => t.id !== id));
    }, props.duration ?? 4000);
  }, []);

  return { toasts, toast };
}

// Standalone toast caller (for use outside React components)
export function toast(props: Omit<ToastItem, "id">) {
  globalToastFn?.(props);
}
