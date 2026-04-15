// eslint-disable-next-line no-unused-vars
import { motion } from "framer-motion";
import { Link } from "react-router-dom";
import { useTheme } from "../context/ThemeContext";
import { useState } from "react";

const links = [
  { href: "/#features", label: "Features" },
  { href: "/#how-it-works", label: "How It Works" },
  { href: "/#get-started", label: "Contact" },
];

export default function Navbar() {
  const { theme, toggleTheme } = useTheme();
  const [mobileOpen, setMobileOpen] = useState(false);

  return (
    <motion.header
      className="fixed top-0 z-50 w-full border-b border-border-soft bg-white/90 backdrop-blur-xl transition-colors duration-500 dark:bg-[#070b14]/90"
      initial={{ opacity: 0, y: -20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.6, ease: "easeOut" }}
    >
      <nav className="mx-auto flex w-full max-w-7xl items-center justify-between px-6 py-5 lg:px-12">
        <Link
          to="/"
          className="font-display text-lg font-semibold tracking-[0.08em] text-slate-900 transition-colors dark:text-white"
        >
          OER AI <span className="text-gradient-gold">AGENT</span>
        </Link>

        <ul className="hidden items-center gap-8 md:flex">
          {links.map((link) => (
            <li key={link.href}>
              <a
                href={link.href}
                className="text-sm font-medium text-slate-600 transition-colors duration-300 hover:text-brand dark:text-slate-300 dark:hover:text-brand"
              >
                {link.label}
              </a>
            </li>
          ))}
        </ul>

        <div className="hidden items-center gap-4 md:flex">
          <button
            type="button"
            onClick={toggleTheme}
            className="inline-flex h-9 w-9 items-center justify-center rounded-full border border-border-soft text-slate-600 transition-all duration-300 hover:border-brand/40 hover:text-brand dark:text-slate-300 dark:hover:text-brand"
            aria-label={`Switch to ${theme === "dark" ? "light" : "dark"} mode`}
          >
            {theme === "dark" ? (
              <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" className="h-4 w-4" stroke="currentColor" strokeWidth={1.8}>
                <circle cx="12" cy="12" r="4.5" />
                <path strokeLinecap="round" d="M12 2.5v2.25M12 19.25v2.25M4.57 4.57l1.59 1.59M17.84 17.84l1.59 1.59M2.5 12h2.25M19.25 12h2.25M4.57 19.43l1.59-1.59M17.84 6.16l1.59-1.59" />
              </svg>
            ) : (
              <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" className="h-4 w-4" stroke="currentColor" strokeWidth={1.8}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M21 12.79A9 9 0 1111.21 3a7 7 0 009.79 9.79z" />
              </svg>
            )}
          </button>
          <Link
            to="/chat"
            className="rounded-full border border-brand/60 bg-brand/10 px-5 py-2 text-xs font-semibold tracking-[0.06em] text-brand transition-all duration-300 hover:bg-brand hover:text-white dark:border-brand/50 dark:bg-brand/10 dark:text-brand-light dark:hover:bg-brand dark:hover:text-white"
          >
            Start Chatting
          </Link>
        </div>

        <button
          type="button"
          onClick={() => setMobileOpen(!mobileOpen)}
          className="inline-flex h-10 w-10 items-center justify-center rounded-lg text-slate-700 dark:text-slate-200 md:hidden"
          aria-label="Toggle menu"
        >
          <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.5} className="h-5 w-5">
            {mobileOpen ? (
              <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
            ) : (
              <path strokeLinecap="round" strokeLinejoin="round" d="M3.75 9h16.5M3.75 15h16.5" />
            )}
          </svg>
        </button>
      </nav>

      {mobileOpen && (
        <motion.div
          className="border-t border-border-soft bg-white/95 px-6 pb-6 backdrop-blur-xl dark:bg-[#070b14]/95 md:hidden"
          initial={{ opacity: 0, height: 0 }}
          animate={{ opacity: 1, height: "auto" }}
          transition={{ duration: 0.3 }}
        >
          <ul className="flex flex-col gap-4 pt-4">
            {links.map((link) => (
              <li key={link.href}>
                <a
                  href={link.href}
                  onClick={() => setMobileOpen(false)}
                  className="text-sm font-medium text-slate-600 dark:text-slate-300"
                >
                  {link.label}
                </a>
              </li>
            ))}
            <li className="flex items-center gap-3 pt-2">
              <button type="button" onClick={toggleTheme} className="text-sm text-slate-600 dark:text-slate-300">
                {theme === "dark" ? "Light Mode" : "Dark Mode"}
              </button>
            </li>
            <li>
              <Link
                to="/chat"
                onClick={() => setMobileOpen(false)}
                className="inline-block rounded-full border border-brand/60 bg-brand/10 px-5 py-2 text-xs font-semibold tracking-[0.06em] text-brand dark:text-brand-light"
              >
                Start Chatting
              </Link>
            </li>
          </ul>
        </motion.div>
      )}
    </motion.header>
  );
}
