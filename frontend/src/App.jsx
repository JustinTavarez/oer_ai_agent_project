import CallToAction from "./components/CallToAction";
import ChatPage from "./components/ChatPage";
import Features from "./components/Features";
import Footer from "./components/Footer";
import Hero from "./components/Hero";
import HowItWorks from "./components/HowItWorks";
import Navbar from "./components/Navbar";
import { useEffect } from "react";
import { Route, Routes, useLocation } from "react-router-dom";
import heroBackground from "./assets/Ai-background.jpeg";

function HomePage() {
  return (
    <>
      <Hero />
      <Features />
      <HowItWorks />
      <CallToAction />
    </>
  );
}

function ScrollToHash() {
  const { hash, pathname } = useLocation();

  useEffect(() => {
    if (!hash) return;

    const id = hash.replace("#", "");
    const scrollToSection = () => {
      const section = document.getElementById(id);
      if (section) {
        section.scrollIntoView({ behavior: "smooth", block: "start" });
      }
    };

    // Delay one frame so home sections are mounted after route transition.
    window.requestAnimationFrame(scrollToSection);
  }, [hash, pathname]);

  return null;
}

function App() {
  return (
    <div
      className="relative min-h-screen bg-surface bg-cover bg-center bg-fixed"
      style={{ backgroundImage: `url(${heroBackground})` }}
    >
      <div className="pointer-events-none absolute inset-0 bg-gradient-to-b from-white/80 via-white/74 to-white/78 transition-colors dark:from-slate-950/84 dark:via-slate-950/78 dark:to-slate-950/82" />
      <div className="relative z-10">
        <ScrollToHash />
        <Navbar />
        <main>
          <Routes>
            <Route path="/" element={<HomePage />} />
            <Route path="/chat" element={<ChatPage />} />
          </Routes>
        </main>
        <Footer />
      </div>
    </div>
  );
}

export default App;
