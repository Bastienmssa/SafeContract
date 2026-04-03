import { Navbar } from "@/components/Navbar";
import { HeroSection } from "@/components/HeroSection";
import { ProblemSolution } from "@/components/ProblemSolution";
import { VisualHook } from "@/components/VisualHook";
import { Footer } from "@/components/Footer";

export default function Home() {
  return (
    <div className="min-h-screen flex flex-col" style={{ background: "#091628" }}>
      <Navbar />
      <main className="flex-1">
        <HeroSection />
        <ProblemSolution />
        <VisualHook />
      </main>
      <Footer />
    </div>
  );
}
