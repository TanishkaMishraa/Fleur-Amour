export function GoldDivider({ className }: { className?: string }) {
  return (
    <div className={`flex items-center gap-4 ${className ?? ""}`}>
      <div className="h-px flex-1 bg-gradient-to-r from-transparent via-brand-gold/30 to-transparent" />
      <div className="h-1 w-1 rotate-45 bg-brand-gold/50" />
      <div className="h-px flex-1 bg-gradient-to-r from-transparent via-brand-gold/30 to-transparent" />
    </div>
  );
}
