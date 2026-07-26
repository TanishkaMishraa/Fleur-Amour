import * as React from "react";
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/lib/utils";

const badgeVariants = cva(
  "inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-2xs font-medium tracking-wide transition-colors",
  {
    variants: {
      variant: {
        default:     "bg-white/[0.06] text-foreground/70 border border-white/[0.08]",
        gold:        "bg-brand-gold/10 text-brand-gold border border-brand-gold/20",
        rose:        "bg-brand-rose/10 text-brand-rose border border-brand-rose/20",
        destructive: "bg-destructive/10 text-destructive border border-destructive/20",
        success:     "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20",
        outline:     "border border-white/10 text-foreground/60",
      },
    },
    defaultVariants: { variant: "default" },
  }
);

export interface BadgeProps
  extends React.HTMLAttributes<HTMLDivElement>,
    VariantProps<typeof badgeVariants> {}

function Badge({ className, variant, ...props }: BadgeProps) {
  return <div className={cn(badgeVariants({ variant }), className)} {...props} />;
}

export { Badge, badgeVariants };
