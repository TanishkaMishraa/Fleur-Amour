import { cn } from "@/lib/utils";

interface LoadingSpinnerProps {
  size?: "sm" | "md" | "lg";
  className?: string;
}

const sizeMap = { sm: "h-4 w-4 border-2", md: "h-6 w-6 border-2", lg: "h-10 w-10 border-[3px]" };

export function LoadingSpinner({ size = "md", className }: LoadingSpinnerProps) {
  return (
    <div
      className={cn(
        "rounded-full border-brand-gold/20 border-t-brand-gold animate-spin",
        sizeMap[size],
        className
      )}
    />
  );
}

export function FullPageLoader() {
  return (
    <div className="fixed inset-0 flex flex-col items-center justify-center bg-brand-black z-50 gap-5">
      <div className="relative">
        <div className="h-14 w-14 rounded-2xl bg-gold-gradient flex items-center justify-center shadow-gold-glow animate-float">
          <span className="text-brand-black text-xl">✦</span>
        </div>
        <div className="absolute -inset-2 rounded-2xl border border-brand-gold/20 animate-spin-slow" />
      </div>
      <LoadingSpinner size="sm" />
    </div>
  );
}
