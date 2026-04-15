import { useEffect, useState } from "react";
import { checkHealth } from "../services/api";

const POLL_INTERVAL = 30_000;

export default function StatusIndicator() {
  const [status, setStatus] = useState({
    backend: "checking",
    lmStudio: "checking",
  });

  useEffect(() => {
    let active = true;

    async function poll() {
      try {
        const data = await checkHealth();
        if (active) {
          setStatus({ backend: "online", lmStudio: data.lm_studio });
        }
      } catch {
        if (active) {
          setStatus({ backend: "offline", lmStudio: "unknown" });
        }
      }
    }

    poll();
    const id = setInterval(poll, POLL_INTERVAL);
    return () => {
      active = false;
      clearInterval(id);
    };
  }, []);

  const backendColor =
    status.backend === "online"
      ? "bg-emerald-400"
      : status.backend === "checking"
        ? "bg-yellow-400"
        : "bg-red-400";

  const llmColor =
    status.lmStudio === "connected"
      ? "bg-emerald-400"
      : status.lmStudio === "checking"
        ? "bg-yellow-400"
        : "bg-red-400";

  const backendLabel =
    status.backend === "online"
      ? "Backend online"
      : status.backend === "checking"
        ? "Checking backend..."
        : "Backend offline";

  const llmLabel =
    status.lmStudio === "connected"
      ? "LLM connected"
      : status.lmStudio === "checking"
        ? "Checking LLM..."
        : "LLM disconnected";

  return (
    <div
      className="flex flex-wrap items-center gap-x-4 gap-y-1 rounded-xl border border-slate-900/12 bg-white/70 px-4 py-2 text-xs text-text-muted dark:border-white/10 dark:bg-white/[0.04]"
      role="status"
      aria-live="polite"
    >
      <span className="inline-flex items-center gap-1.5">
        <span className={`h-2 w-2 rounded-full ${backendColor}`} aria-hidden="true" />
        {backendLabel}
      </span>
      <span className="inline-flex items-center gap-1.5">
        <span className={`h-2 w-2 rounded-full ${llmColor}`} aria-hidden="true" />
        {llmLabel}
      </span>
    </div>
  );
}
