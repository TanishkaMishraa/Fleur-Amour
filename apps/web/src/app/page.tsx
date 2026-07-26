import { Navbar } from "@/components/layout/Navbar";
import { Footer } from "@/components/layout/Footer";
import { LandingHero } from "@/components/features/landing/LandingHero";
import { LandingFeatures } from "@/components/features/landing/LandingFeatures";
import { LandingHowItWorks } from "@/components/features/landing/LandingHowItWorks";
import { LandingCTA } from "@/components/features/landing/LandingCTA";

export default function HomePage() {
  return (
    <div className="relative min-h-screen bg-brand-black noise">
      {/* Ambient background */}
      <div className="pointer-events-none fixed inset-0 overflow-hidden">
        <div className="absolute -top-40 left-1/2 -translate-x-1/2 h-[600px] w-[600px] rounded-full bg-brand-gold/[0.06] blur-[120px]" />
        <div className="absolute top-1/3 -right-40 h-[400px] w-[400px] rounded-full bg-brand-rose/[0.04] blur-[100px]" />
        <div className="absolute bottom-0 left-0 h-[300px] w-[400px] rounded-full bg-brand-gold/[0.03] blur-[80px]" />
      </div>

      <Navbar />
      <main className="relative z-10">
        <LandingHero />
        <LandingFeatures />
        <LandingHowItWorks />
        <LandingCTA />
      </main>
      <Footer />
    </div>
  );
}
