import Link from "next/link";
import { Sparkles } from "lucide-react";
import { Separator } from "@/components/ui/separator";

const LINKS = {
  Product:   [{ label: "Features", href: "/#features" }, { label: "How It Works", href: "/#how-it-works" }, { label: "Pricing", href: "/#pricing" }],
  Company:   [{ label: "About", href: "/about" }, { label: "Blog", href: "/blog" }, { label: "Careers", href: "/careers" }],
  Legal:     [{ label: "Privacy", href: "/privacy" }, { label: "Terms", href: "/terms" }, { label: "Cookies", href: "/cookies" }],
};

export function Footer() {
  return (
    <footer className="border-t border-white/[0.06] bg-brand-black/50 backdrop-blur-sm">
      <div className="container py-16">
        <div className="grid grid-cols-2 gap-10 md:grid-cols-5">
          {/* Brand */}
          <div className="col-span-2 space-y-4">
            <Link href="/" className="flex items-center gap-2.5">
              <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-gold-gradient">
                <Sparkles className="h-4 w-4 text-brand-black" />
              </div>
              <span className="font-display text-xl font-medium">
                Aura<span className="text-gold-gradient">Fit</span>
              </span>
            </Link>
            <p className="max-w-xs text-sm leading-relaxed text-muted-foreground">
              AI-powered beauty, skincare, fragrance, and personal styling — curated to your unique profile.
            </p>
            <p className="text-xs text-muted-foreground/50 tracking-wider uppercase">
              Crafted with precision · 2025
            </p>
          </div>

          {/* Link columns */}
          {Object.entries(LINKS).map(([section, links]) => (
            <div key={section} className="space-y-4">
              <h4 className="text-xs font-medium tracking-widest uppercase text-muted-foreground/60">{section}</h4>
              <ul className="space-y-3">
                {links.map((link) => (
                  <li key={link.href}>
                    <Link href={link.href}
                      className="text-sm text-muted-foreground hover:text-foreground transition-colors duration-200">
                      {link.label}
                    </Link>
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>

        <Separator className="my-10" />

        <div className="flex flex-col items-center gap-4 sm:flex-row sm:justify-between">
          <p className="text-xs text-muted-foreground/50">
            © {new Date().getFullYear()} AuraFit. All rights reserved.
          </p>
          <p className="text-xs text-muted-foreground/30 tracking-widest uppercase">
            Stage 2 · Frontend Foundation
          </p>
        </div>
      </div>
    </footer>
  );
}
