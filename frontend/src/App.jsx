import CallToAction from "./components/CallToAction";
import ChatPage from "./components/ChatPage";
import Features from "./components/Features";
import Footer from "./components/Footer";
import Hero from "./components/Hero";
import HowItWorks from "./components/HowItWorks";
import Navbar from "./components/Navbar";
import { useEffect } from "react";
import { Route, Routes, useLocation } from "react-router-dom";

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

    window.requestAnimationFrame(scrollToSection);
  }, [hash, pathname]);

  return null;
}

function App() {
  return (
    <div className="min-h-screen bg-surface transition-colors duration-500">
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
  );
}

export default App;
