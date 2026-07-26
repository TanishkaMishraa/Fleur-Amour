import type { Config } from "tailwindcss";
import { fontFamily } from "tailwindcss/defaultTheme";
import animate from "tailwindcss-animate";

const config: Config = {
  darkMode: ["class"],
  content: [
    "./src/pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/components/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    container: {
      center: true,
      padding: { DEFAULT: "1.5rem", sm: "2rem", lg: "4rem", xl: "5rem", "2xl": "6rem" },
      screens: { "2xl": "1400px" },
    },
    extend: {
      // ── AuraFit Design Token Colors ──────────────────────────────────────
      colors: {
        // Brand: obsidian black + champagne gold + warm ivory
        brand: {
          black:     "#0A0A0B",
          charcoal:  "#141416",
          graphite:  "#1C1C1F",
          slate:     "#2C2C2F",
          mist:      "#3A3A3E",
          silver:    "#8A8A8F",
          pearl:     "#C4C4C8",
          ivory:     "#F5F0E8",
          cream:     "#FAF7F2",
          white:     "#FEFEFE",
          // Signature gold gradient stops
          gold:      "#C9A84C",
          "gold-light": "#E8C96C",
          "gold-dark":  "#A07830",
          "gold-muted": "#8B6B3D",
          // Accent rose for beauty/cosmetics
          rose:      "#D4818A",
          "rose-light": "#EBB4BB",
          "rose-muted": "#9A5A62",
        },

        // Semantic (CSS var driven — see globals.css)
        background:     "hsl(var(--background))",
        foreground:     "hsl(var(--foreground))",
        card:           { DEFAULT: "hsl(var(--card))", foreground: "hsl(var(--card-foreground))" },
        popover:        { DEFAULT: "hsl(var(--popover))", foreground: "hsl(var(--popover-foreground))" },
        primary:        { DEFAULT: "hsl(var(--primary))", foreground: "hsl(var(--primary-foreground))" },
        secondary:      { DEFAULT: "hsl(var(--secondary))", foreground: "hsl(var(--secondary-foreground))" },
        muted:          { DEFAULT: "hsl(var(--muted))", foreground: "hsl(var(--muted-foreground))" },
        accent:         { DEFAULT: "hsl(var(--accent))", foreground: "hsl(var(--accent-foreground))" },
        destructive:    { DEFAULT: "hsl(var(--destructive))", foreground: "hsl(var(--destructive-foreground))" },
        border:         "hsl(var(--border))",
        input:          "hsl(var(--input))",
        ring:           "hsl(var(--ring))",
        chart: {
          "1": "hsl(var(--chart-1))", "2": "hsl(var(--chart-2))",
          "3": "hsl(var(--chart-3))", "4": "hsl(var(--chart-4))", "5": "hsl(var(--chart-5))",
        },
        sidebar: {
          DEFAULT: "hsl(var(--sidebar-background))",
          foreground: "hsl(var(--sidebar-foreground))",
          primary: "hsl(var(--sidebar-primary))",
          "primary-foreground": "hsl(var(--sidebar-primary-foreground))",
          accent: "hsl(var(--sidebar-accent))",
          "accent-foreground": "hsl(var(--sidebar-accent-foreground))",
          border: "hsl(var(--sidebar-border))",
          ring: "hsl(var(--sidebar-ring))",
        },
      },

      // ── Typography ────────────────────────────────────────────────────────
      fontFamily: {
        // Display: Cormorant Garamond — editorial luxury
        display: ["var(--font-cormorant)", "Georgia", "serif"],
        // Body: DM Sans — clean, modern, Apple-adjacent
        sans:    ["var(--font-dm-sans)", ...fontFamily.sans],
        // Mono: JetBrains Mono — technical elements
        mono:    ["var(--font-jetbrains-mono)", ...fontFamily.mono],
        // Accent: Playfair Display — pull-quotes, hero text
        accent:  ["var(--font-playfair)", "Georgia", "serif"],
      },

      fontSize: {
        "2xs": ["0.625rem", { lineHeight: "0.875rem" }],
        "display-2xl": ["4.5rem",  { lineHeight: "1.1",  letterSpacing: "-0.04em" }],
        "display-xl":  ["3.75rem", { lineHeight: "1.1",  letterSpacing: "-0.03em" }],
        "display-lg":  ["3rem",    { lineHeight: "1.15", letterSpacing: "-0.02em" }],
        "display-md":  ["2.25rem", { lineHeight: "1.2",  letterSpacing: "-0.02em" }],
        "display-sm":  ["1.875rem",{ lineHeight: "1.25", letterSpacing: "-0.01em" }],
      },

      letterSpacing: {
        tightest: "-0.04em",
        tighter:  "-0.02em",
        widest:   "0.2em",
        "ultra-wide": "0.3em",
      },

      // ── Spacing ───────────────────────────────────────────────────────────
      spacing: {
        "18": "4.5rem", "22": "5.5rem", "30": "7.5rem",
        "34": "8.5rem", "66": "16.5rem", "72": "18rem",
        "76": "19rem",  "80": "20rem",  "88": "22rem",
        "screen-minus-nav": "calc(100vh - 4.5rem)",
      },

      // ── Border radius ─────────────────────────────────────────────────────
      borderRadius: {
        lg: "var(--radius)",
        md: "calc(var(--radius) - 2px)",
        sm: "calc(var(--radius) - 4px)",
        "2xl": "1rem", "3xl": "1.5rem", "4xl": "2rem",
      },

      // ── Box shadows — layered for depth ───────────────────────────────────
      boxShadow: {
        "luxury-sm":  "0 1px 3px rgba(0,0,0,0.08), 0 1px 2px rgba(0,0,0,0.04)",
        "luxury":     "0 4px 16px rgba(0,0,0,0.12), 0 2px 4px rgba(0,0,0,0.08)",
        "luxury-lg":  "0 16px 48px rgba(0,0,0,0.16), 0 4px 12px rgba(0,0,0,0.08)",
        "luxury-xl":  "0 24px 80px rgba(0,0,0,0.20), 0 8px 24px rgba(0,0,0,0.10)",
        "gold-glow":  "0 0 30px rgba(201,168,76,0.25), 0 0 60px rgba(201,168,76,0.10)",
        "gold-sm":    "0 0 12px rgba(201,168,76,0.20)",
        "inner-luxury": "inset 0 1px 0 rgba(255,255,255,0.08)",
        "card-hover": "0 20px 60px rgba(0,0,0,0.18), 0 8px 20px rgba(0,0,0,0.10)",
      },

      // ── Backgrounds ───────────────────────────────────────────────────────
      backgroundImage: {
        "gold-gradient":     "linear-gradient(135deg, #C9A84C 0%, #E8C96C 50%, #A07830 100%)",
        "gold-shimmer":      "linear-gradient(90deg, #A07830 0%, #E8C96C 50%, #A07830 100%)",
        "hero-gradient":     "radial-gradient(ellipse 80% 60% at 50% -20%, rgba(201,168,76,0.15) 0%, transparent 60%)",
        "dark-mesh":         "radial-gradient(at 40% 20%, rgba(201,168,76,0.08) 0px, transparent 50%), radial-gradient(at 80% 0%, rgba(212,129,138,0.06) 0px, transparent 50%), radial-gradient(at 0% 50%, rgba(201,168,76,0.04) 0px, transparent 50%)",
        "card-shimmer":      "linear-gradient(135deg, rgba(255,255,255,0.05) 0%, rgba(255,255,255,0) 100%)",
        "noise":             "url('/images/noise.png')",
        "sidebar-gradient":  "linear-gradient(180deg, #0A0A0B 0%, #141416 100%)",
      },

      // ── Animations ────────────────────────────────────────────────────────
      keyframes: {
        "accordion-down":    { from: { height: "0" }, to: { height: "var(--radix-accordion-content-height)" } },
        "accordion-up":      { from: { height: "var(--radix-accordion-content-height)" }, to: { height: "0" } },
        "fade-in":           { from: { opacity: "0" }, to: { opacity: "1" } },
        "fade-up":           { from: { opacity: "0", transform: "translateY(20px)" }, to: { opacity: "1", transform: "translateY(0)" } },
        "fade-down":         { from: { opacity: "0", transform: "translateY(-20px)" }, to: { opacity: "1", transform: "translateY(0)" } },
        "scale-in":          { from: { opacity: "0", transform: "scale(0.96)" }, to: { opacity: "1", transform: "scale(1)" } },
        "slide-in-left":     { from: { transform: "translateX(-100%)", opacity: "0" }, to: { transform: "translateX(0)", opacity: "1" } },
        "shimmer":           { "0%": { backgroundPosition: "-200% 0" }, "100%": { backgroundPosition: "200% 0" } },
        "gold-pulse":        { "0%, 100%": { opacity: "1" }, "50%": { opacity: "0.6" } },
        "float":             { "0%, 100%": { transform: "translateY(0px)" }, "50%": { transform: "translateY(-8px)" } },
        "spin-slow":         { from: { transform: "rotate(0deg)" }, to: { transform: "rotate(360deg)" } },
        "border-flow":       { "0%, 100%": { backgroundPosition: "0% 50%" }, "50%": { backgroundPosition: "100% 50%" } },
      },
      animation: {
        "accordion-down": "accordion-down 0.2s ease-out",
        "accordion-up":   "accordion-up 0.2s ease-out",
        "fade-in":        "fade-in 0.4s ease-out",
        "fade-up":        "fade-up 0.5s ease-out",
        "fade-down":      "fade-down 0.5s ease-out",
        "scale-in":       "scale-in 0.3s ease-out",
        "slide-in-left":  "slide-in-left 0.4s ease-out",
        "shimmer":        "shimmer 2.5s linear infinite",
        "gold-pulse":     "gold-pulse 3s ease-in-out infinite",
        "float":          "float 6s ease-in-out infinite",
        "spin-slow":      "spin-slow 8s linear infinite",
        "border-flow":    "border-flow 4s ease infinite",
      },

      // ── Transitions ───────────────────────────────────────────────────────
      transitionTimingFunction: {
        "luxury":   "cubic-bezier(0.23, 1, 0.32, 1)",
        "spring":   "cubic-bezier(0.34, 1.56, 0.64, 1)",
        "smooth":   "cubic-bezier(0.4, 0, 0.2, 1)",
      },
      transitionDuration: {
        "250": "250ms", "350": "350ms", "400": "400ms", "600": "600ms",
      },
    },
  },
  plugins: [animate],
};

export default config;
