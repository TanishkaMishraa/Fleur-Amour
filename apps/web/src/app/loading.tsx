import { Sparkles } from "lucide-react";
export default function Loading() {
  return (
    <div className="fixed inset-0 flex items-center justify-center bg-brand-black z-50">
      <div className="flex flex-col items-center gap-5">
        <div className="relative">
          <div className="h-14 w-14 rounded-2xl bg-gold-gradient flex items-center justify-center shadow-gold-glow animate-float">
            <Sparkles className="h-6 w-6 text-brand-black" />
          </div>
          <div className="absolute -inset-2 rounded-2xl border border-brand-gold/20 animate-spin-slow" />
        </div>
        <div className="flex gap-1.5">
          {[0, 1, 2].map((i) => (
            <div key={i} className="h-1.5 w-1.5 rounded-full bg-brand-gold animate-gold-pulse"
              style={{ animationDelay: `${i * 0.2}s` }} />
          ))}
        </div>
      </div>
    </div>
  );
}
