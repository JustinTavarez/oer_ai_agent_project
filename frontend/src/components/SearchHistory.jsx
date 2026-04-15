import { useState, useEffect } from "react";

const STORAGE_KEY = "oer-search-history";
const MAX_ENTRIES = 15;

function load() {
  try {
    return JSON.parse(localStorage.getItem(STORAGE_KEY) || "[]");
  } catch {
    return [];
  }
}

function save(entries) {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(entries));
}

export function addToHistory(query) {
  const trimmed = query.trim();
  if (!trimmed) return;
  const entries = load().filter((e) => e !== trimmed);
  entries.unshift(trimmed);
  save(entries.slice(0, MAX_ENTRIES));
}

export default function SearchHistory({ onSelect }) {
  const [entries, setEntries] = useState([]);
  const [open, setOpen] = useState(false);

  useEffect(() => {
    setEntries(load());
  }, [open]);

  const handleClear = () => {
    save([]);
    setEntries([]);
  };

  if (entries.length === 0 && !open) return null;

  return (
    <div className="w-full">
      <button
        type="button"
        onClick={() => setOpen((p) => !p)}
        className="flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-xs font-medium text-text-muted transition hover:bg-slate-900/5 hover:text-slate-800 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand/35 dark:hover:bg-white/5 dark:hover:text-white dark:focus-visible:ring-brand-light"
        aria-expanded={open}
      >
        <svg
          xmlns="http://www.w3.org/2000/svg"
          className="h-3.5 w-3.5"
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
          strokeWidth={2}
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"
          />
        </svg>
        {open ? "Hide" : "Recent searches"}
        {!open && entries.length > 0 && (
          <span className="rounded-full bg-slate-900/10 px-1.5 py-0.5 text-[10px] dark:bg-white/10">
            {entries.length}
          </span>
        )}
      </button>

      {open && (
        <div className="mt-2 rounded-xl border border-slate-900/12 bg-white/75 p-3 dark:border-white/10 dark:bg-white/[0.03]">
          {entries.length === 0 ? (
            <p className="text-xs text-text-muted">No recent searches.</p>
          ) : (
            <>
              <div className="flex flex-wrap gap-2">
                {entries.map((entry, i) => (
                  <button
                    key={`${entry}-${i}`}
                    type="button"
                    onClick={() => {
                      onSelect(entry);
                      setOpen(false);
                    }}
                    className="max-w-[240px] truncate rounded-full border border-slate-900/12 bg-white/90 px-3 py-1 text-xs text-slate-700 transition hover:border-brand/40 hover:text-slate-900 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand/35 dark:border-white/10 dark:bg-white/[0.04] dark:text-slate-300 dark:hover:border-brand-light/40 dark:hover:text-white dark:focus-visible:ring-brand-light"
                  >
                    {entry}
                  </button>
                ))}
              </div>
              <button
                type="button"
                onClick={handleClear}
                className="mt-2 text-xs text-red-400 transition hover:text-red-300 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-red-400"
              >
                Clear all
              </button>
            </>
          )}
        </div>
      )}
    </div>
  );
}
