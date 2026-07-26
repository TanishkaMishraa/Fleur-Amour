import type { Metadata, Viewport } from "next";
import { Cormorant_Garamond, DM_Sans, Playfair_Display } from "next/font/google";
import { ThemeProvider } from "@/components/shared/ThemeProvider";
import { QueryProvider } from "@/components/shared/QueryProvider";
import { Toaster } from "@/components/shared/Toaster";
import "@/styles/globals.css";

const cormorant = Cormorant_Garamond({
  subsets: ["latin"],
  weight: ["300", "400", "500", "600", "700"],
  style: ["normal", "italic"],
  variable: "--font-cormorant",
  display: "swap",
});

const dmSans = DM_Sans({
  subsets: ["latin"],
  weight: ["300", "400", "500", "600"],
  style: ["normal", "italic"],
  variable: "--font-dm-sans",
  display: "swap",
});

const playfair = Playfair_Display({
  subsets: ["latin"],
  weight: ["400", "600"],
  style: ["normal", "italic"],
  variable: "--font-playfair",
  display: "swap",
});

export const metadata: Metadata = {
  title: {
    default: "AuraFit — Your AI Beauty & Style Curator",
    template: "%s · AuraFit",
  },
  description:
    "Personalised AI-powered beauty, skincare, fragrance, and personal styling — crafted to your unique profile.",
  keywords: ["beauty", "skincare", "AI styling", "fragrance", "wardrobe", "personal stylist"],
  authors: [{ name: "AuraFit" }],
  openGraph: {
    type: "website",
    locale: "en_US",
    url: "https://aurafit.ai",
    siteName: "AuraFit",
    title: "AuraFit — Your AI Beauty & Style Curator",
    description: "Personalised AI-powered beauty, skincare, fragrance, and personal styling.",
  },
  twitter: {
    card: "summary_large_image",
    title: "AuraFit",
    description: "Your AI Beauty & Style Curator",
  },
  robots: { index: true, follow: true },
};

export const viewport: Viewport = {
  themeColor: [{ media: "(prefers-color-scheme: dark)", color: "#09090B" }],
  width: "device-width",
  initialScale: 1,
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html
      lang="en"
      suppressHydrationWarning
      className={`${cormorant.variable} ${dmSans.variable} ${playfair.variable}`}
    >
      <body className="min-h-screen bg-background antialiased">
        <ThemeProvider
          attribute="class"
          defaultTheme="dark"
          enableSystem={false}
          disableTransitionOnChange
        >
          <QueryProvider>
            {children}
            <Toaster />
          </QueryProvider>
        </ThemeProvider>
      </body>
    </html>
  );
}
