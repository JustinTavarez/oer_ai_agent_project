// eslint-disable-next-line no-unused-vars
import { motion } from "framer-motion";
import { Link } from "react-router-dom";
import { useTheme } from "../context/ThemeContext";

const links = [
  { href: "/#features", label: "Features" },
  { href: "/#how-it-works", label: "How It Works" },
];

export default function Navbar() {
  const { theme, toggleTheme } = useTheme();

  return (
    <motion.header
      className="sticky top-0 z-50 border-b border-slate-900/12 bg-white/85 backdrop-blur-xl transition-colors dark:border-white/15 dark:bg-slate-950/68"
      initial={{ opacity: 0, y: -30 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.7, ease: "easeOut" }}
    >
      <nav className="mx-auto flex w-full max-w-6xl items-center justify-between px-6 py-4 md:px-10">
        <Link
          to="/"
          className="text-sm font-semibold tracking-[0.14em] text-slate-900 transition-colors dark:text-slate-50"
        >
          OER AI AGENT
        </Link>
        <ul className="hidden items-center gap-4 text-sm text-slate-700 dark:text-slate-200 md:flex">
          {links.map((link) => (
            <li key={link.href}>
              <a
                href={link.href}
                className="transition-colors duration-300 hover:text-brand dark:hover:text-brand-light"
              >
                {link.label}
              </a>
            </li>
          ))}
          <li>
            <button
              type="button"
              onClick={toggleTheme}
              className="inline-flex h-9 w-9 items-center justify-center rounded-full border border-slate-900/15 bg-white/70 text-slate-700 transition hover:border-brand/45 hover:text-brand focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-light/50 dark:border-white/15 dark:bg-white/10 dark:text-slate-200 dark:hover:border-brand-light/50 dark:hover:text-brand-light"
              aria-label={`Switch to ${theme === "dark" ? "light" : "dark"} mode`}
              title={`Switch to ${theme === "dark" ? "light" : "dark"} mode`}
            >
              {theme === "dark" ? (
                <svg
                  xmlns="http://www.w3.org/2000/svg"
                  viewBox="0 0 24 24"
                  fill="none"
                  className="h-4.5 w-4.5"
                  stroke="currentColor"
                  strokeWidth={1.8}
                >
                  <circle cx="12" cy="12" r="4.5" />
                  <path strokeLinecap="round" d="M12 2.5v2.25M12 19.25v2.25M4.57 4.57l1.59 1.59M17.84 17.84l1.59 1.59M2.5 12h2.25M19.25 12h2.25M4.57 19.43l1.59-1.59M17.84 6.16l1.59-1.59" />
                </svg>
              ) : (
                <svg
                  xmlns="http://www.w3.org/2000/svg"
                  viewBox="0 0 24 24"
                  fill="none"
                  className="h-4.5 w-4.5"
                  stroke="currentColor"
                  strokeWidth={1.8}
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    d="M21 12.79A9 9 0 1111.21 3a7 7 0 009.79 9.79z"
                  />
                </svg>
              )}
            </button>
          </li>
          <li>
            <Link
              to="/chat"
              className="rounded-full bg-gradient-to-r from-brand to-indigo-500 px-4 py-2 text-xs font-semibold text-white transition-all duration-300 hover:scale-105 hover:shadow-2xl hover:shadow-brand/35"
            >
              Start Chatting
            </Link>
          </li>
        </ul>
      </nav>
    </motion.header>
  );
}
