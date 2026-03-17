// eslint-disable-next-line no-unused-vars
import { motion } from "framer-motion";
import { Link } from "react-router-dom";

const links = [
  { href: "/#features", label: "Features" },
  { href: "/#how-it-works", label: "How It Works" },
];

export default function Navbar() {
  return (
    <motion.header
      className="sticky top-0 z-50 border-b border-white/10 bg-black/45 backdrop-blur-xl"
      initial={{ opacity: 0, y: -30 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.7, ease: "easeOut" }}
    >
      <nav className="mx-auto flex w-full max-w-6xl items-center justify-between px-6 py-4 md:px-10">
        <Link to="/" className="text-sm font-semibold tracking-[0.14em] text-white">
          OER AI AGENT
        </Link>
        <ul className="hidden items-center gap-7 text-sm text-slate-200 md:flex">
          {links.map((link) => (
            <li key={link.href}>
              <a
                href={link.href}
                className="transition-colors duration-300 hover:text-brand-light"
              >
                {link.label}
              </a>
            </li>
          ))}
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
