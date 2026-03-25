import { Link } from "react-router-dom";

const footerLinks = {
  Product: [
    { label: "Start Chatting", to: "/chat" },
    { label: "Features", href: "/#features" },
    { label: "How It Works", href: "/#how-it-works" },
  ],
  Resources: [
    { label: "OpenALG", href: "https://openalg.org", external: true },
    { label: "OER Commons", href: "https://oercommons.org", external: true },
  ],
  Developer: [
    { label: "GitHub", href: "https://github.com/JustinTavarez", external: true },
  ],
};

export default function Footer() {
  return (
    <footer className="border-t border-border-soft bg-white/80 px-6 py-16 backdrop-blur-sm transition-colors dark:bg-[#070b14]/80 lg:px-12">
      <div className="mx-auto max-w-7xl">
        <div className="grid gap-12 md:grid-cols-4">
          <div>
            <p className="font-display text-lg font-semibold tracking-[0.08em] text-slate-900 dark:text-white">
              OER AI <span className="text-gradient-gold">AGENT</span>
            </p>
            <p className="mt-4 max-w-xs text-sm leading-relaxed text-text-muted">
              AI-powered open educational resource discovery. Making quality learning accessible to everyone.
            </p>
          </div>

          {Object.entries(footerLinks).map(([category, links]) => (
            <div key={category}>
              <h4 className="mb-4 text-xs font-semibold tracking-[0.16em] text-slate-500 dark:text-slate-400">
                {category.toUpperCase()}
              </h4>
              <ul className="space-y-3">
                {links.map((link) => (
                  <li key={link.label}>
                    {link.to ? (
                      <Link
                        to={link.to}
                        className="text-sm text-text-muted transition-colors duration-300 hover:text-brand dark:hover:text-brand-light"
                      >
                        {link.label}
                      </Link>
                    ) : (
                      <a
                        href={link.href}
                        target={link.external ? "_blank" : undefined}
                        rel={link.external ? "noreferrer" : undefined}
                        className="text-sm text-text-muted transition-colors duration-300 hover:text-brand dark:hover:text-brand-light"
                      >
                        {link.label}
                      </a>
                    )}
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>

        <div className="mt-16 flex flex-col items-center justify-between gap-4 border-t border-border-soft pt-8 text-xs text-text-muted md:flex-row">
          <p>{new Date().getFullYear()} &copy; OER AI Agent. All rights reserved.</p>
          <p>Created by Justin Tavarez</p>
        </div>
      </div>
    </footer>
  );
}
