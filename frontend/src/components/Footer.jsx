export default function Footer() {
  return (
    <footer className="border-t border-slate-900/15 bg-white/80 px-6 py-10 backdrop-blur-md dark:border-white/15 dark:bg-slate-950/55 md:px-10">
      <div className="mx-auto flex w-full max-w-6xl flex-col items-center justify-between gap-3 text-sm text-slate-700 dark:text-slate-300 md:flex-row">
        <p>Created by Justin Tavarez</p>
        <a
          href="https://github.com/JustinTavarez"
          target="_blank"
          rel="noreferrer"
          className="transition-colors duration-300 hover:text-brand dark:hover:text-brand-light"
        >
          My GitHub
        </a>
        <p>{new Date().getFullYear()}© All rights reserved.</p>
      </div>
    </footer>
  );
}
