"use client";
import * as React from "react";
import { cn } from "@/lib/utils";

export interface InputProps extends React.InputHTMLAttributes<HTMLInputElement> {
  label?: string;
  error?: string;
  hint?: string;
}

const Input = React.forwardRef<HTMLInputElement, InputProps>(
  ({ className, type, label, error, hint, id, ...props }, ref) => {
    const inputId = id ?? label?.toLowerCase().replace(/\s+/g, "-");
    return (
      <div className="space-y-1.5">
        {label && (
          <label htmlFor={inputId}
            className="block text-xs font-medium tracking-wide text-muted-foreground/80">
            {label}
          </label>
        )}
        <input
          id={inputId}
          type={type}
          className={cn(
            "input-luxury",
            error && "border-destructive/50 focus:border-destructive/70 focus:ring-destructive/20",
            className
          )}
          ref={ref}
          {...props}
        />
        {error && <p className="text-xs text-destructive">{error}</p>}
        {hint && !error && <p className="text-xs text-muted-foreground/50">{hint}</p>}
      </div>
    );
  }
);
Input.displayName = "Input";

export { Input };
