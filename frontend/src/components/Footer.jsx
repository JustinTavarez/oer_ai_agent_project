export default function Footer() {
  return (
    <footer className="border-t border-white/12 px-6 py-10 md:px-10">
      <div className="mx-auto flex w-full max-w-6xl flex-col items-center justify-between gap-3 text-sm text-slate-400 md:flex-row">
        <p>OER AI Agent</p>
        <a
          href="https://github.com/vitejs/vite"
          target="_blank"
          rel="noreferrer"
          className="transition-colors duration-300 hover:text-brand-light"
        >
          GitHub
        </a>
        <p>{new Date().getFullYear()} All rights reserved.</p>
      </div>
    </footer>
  );
}
