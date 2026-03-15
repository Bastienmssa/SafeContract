import { Navbar } from "@/components/Navbar";
import { HeroSection } from "@/components/HeroSection";
import { SocialProof } from "@/components/SocialProof";
import { ProblemSolution } from "@/components/ProblemSolution";
import { VisualHook } from "@/components/VisualHook";
import { Pricing } from "@/components/Pricing";
import { Footer } from "@/components/Footer";

export default function Home() {
  return (
    <div className="min-h-screen flex flex-col bg-white">
      <Navbar />
      <main className="flex-1">
        <HeroSection />
        <SocialProof />
        <ProblemSolution />
        <VisualHook />
        <Pricing />
      </main>
      <Footer />
    </div>
  );
}
