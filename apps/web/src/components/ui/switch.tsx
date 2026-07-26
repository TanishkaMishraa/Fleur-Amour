"use client";
/**
 * AuraFit — Switch UI component.
 * Used throughout settings and preference panels.
 * Matches the luxury dark design system.
 */
import * as React from "react";
import { cn } from "@/lib/utils";

export interface SwitchProps {
  checked:          boolean;
  onCheckedChange:  (value: boolean) => void;
  disabled?:        boolean;
  id?:              string;
  className?:       string;
  "aria-label"?:    string;
}

const Switch = React.forwardRef<HTMLButtonElement, SwitchProps>(
  ({ checked, onCheckedChange, disabled, id, className, ...props }, ref) => {
    return (
      <button
        ref={ref}
        id={id}
        type="button"
        role="switch"
        aria-checked={checked}
        disabled={disabled}
        onClick={() => !disabled && onCheckedChange(!checked)}
        className={cn(
          // Track
          "relative inline-flex h-5 w-9 shrink-0 cursor-pointer items-center rounded-full",
          "border-2 border-transparent outline-none transition-colors duration-200",
          "focus-visible:ring-2 focus-visible:ring-brand-gold/40 focus-visible:ring-offset-2 focus-visible:ring-offset-background",
          "disabled:cursor-not-allowed disabled:opacity-40",
          checked ? "bg-brand-gold" : "bg-white/[0.1]",
          className
        )}
        {...props}
      >
        {/* Thumb */}
        <span
          className={cn(
            "pointer-events-none block h-4 w-4 rounded-full shadow-md ring-0 transition-transform duration-200",
            checked
              ? "translate-x-4 bg-brand-black"
              : "translate-x-0 bg-white/70"
          )}
        />
      </button>
    );
  }
);
Switch.displayName = "Switch";

export { Switch };
