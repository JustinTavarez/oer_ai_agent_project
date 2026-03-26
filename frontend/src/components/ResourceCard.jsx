import { useState } from "react";

const LICENSE_COLORS = {
  open: "border-emerald-500/30 bg-emerald-500/10 text-emerald-300",
  unclear: "border-yellow-500/30 bg-yellow-500/10 text-yellow-300",
  not_open: "border-red-500/30 bg-red-500/10 text-red-300",
  unknown: "border-slate-500/30 bg-slate-500/10 text-slate-400",
};

const BASIS_LABELS = {
  verified: "Verified",
  inferred: "Inferred",
  unavailable: "N/A",
};

function ScoreBar({ score, max = 5 }) {
  const pct = Math.round((score / max) * 100);
  return (
    <div className="flex items-center gap-2">
      <div className="h-1.5 flex-1 rounded-full bg-white/10">
        <div
          className="h-full rounded-full bg-gradient-to-r from-brand to-indigo-400"
          style={{ width: `${pct}%` }}
        />
      </div>
      <span className="text-xs tabular-nums text-slate-400">{score.toFixed(1)}</span>
    </div>
  );
}

function RubricRow({ label, data }) {
  if (!data) return null;
  return (
    <div className="flex flex-col gap-0.5">
      <div className="flex items-center justify-between">
        <span className="text-xs text-slate-300">{label}</span>
        <span className="text-[10px] text-slate-500">{BASIS_LABELS[data.basis] ?? ""}</span>
      </div>
      <ScoreBar score={data.score} />
      {data.reasoning && (
        <p className="text-[11px] leading-snug text-slate-500">{data.reasoning}</p>
      )}
    </div>
  );
}

const RUBRIC_LABELS = {
  relevance_and_comprehensiveness: "Relevance & Comprehensiveness",
  interactivity_and_engagement: "Interactivity & Engagement",
  pedagogical_soundness: "Pedagogical Soundness",
  licensing_clarity: "Licensing Clarity",
  accessibility_compliance: "Accessibility Compliance",
  modularity_and_adaptability: "Modularity & Adaptability",
  supplementary_resources: "Supplementary Resources",
};

export default function ResourceCard({ resource }) {
  const [rubricOpen, setRubricOpen] = useState(false);

  const license = resource.license ?? {};
  const licenseStyle = LICENSE_COLORS[license.status] ?? LICENSE_COLORS.unknown;
  const rubric = resource.rubric_evaluation ?? {};
  const relevance = resource.relevance ?? {};

  return (
    <div className="flex flex-col rounded-2xl border border-white/10 bg-white/[0.04] p-4 transition hover:border-white/20">
      <h3 className="text-base font-semibold text-white">{resource.title}</h3>

      {resource.description && (
        <p className="mt-1.5 text-sm leading-relaxed text-slate-300">
          {resource.description}
        </p>
      )}

      {/* Meta row */}
      <div className="mt-3 flex flex-wrap items-center gap-2">
        {license.status && (
          <span
            className={`inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-medium ${licenseStyle}`}
          >
            {license.details || license.status}
          </span>
        )}
        {resource.source && (
          <span className="inline-flex items-center rounded-full border border-blue-500/30 bg-blue-500/10 px-2.5 py-0.5 text-xs font-medium text-blue-300">
            {resource.source}
          </span>
        )}
        {resource.course_code && (
          <span className="inline-flex items-center rounded-full border border-white/15 bg-white/5 px-2.5 py-0.5 text-xs font-medium text-slate-300">
            {resource.course_code}
          </span>
        )}
      </div>

      {/* Relevance */}
      {relevance.score > 0 && (
        <div className="mt-3">
          <span className="text-xs font-medium uppercase tracking-wide text-brand-light">
            Relevance
          </span>
          <ScoreBar score={relevance.score} max={1} />
          {relevance.reasoning && (
            <p className="mt-0.5 text-[11px] text-slate-500">{relevance.reasoning}</p>
          )}
        </div>
      )}

      {/* Integration tips */}
      {resource.integration_tips?.length > 0 && (
        <div className="mt-3">
          <span className="text-xs font-medium uppercase tracking-wide text-brand-light">
            Integration Tips
          </span>
          <ul className="mt-1 list-inside list-disc space-y-0.5 text-sm text-slate-300">
            {resource.integration_tips.map((tip, i) => (
              <li key={i}>{tip}</li>
            ))}
          </ul>
        </div>
      )}

      {/* Rubric evaluation (collapsible) */}
      {Object.keys(rubric).length > 0 && (
        <div className="mt-3">
          <button
            type="button"
            onClick={() => setRubricOpen((p) => !p)}
            className="flex items-center gap-1.5 text-xs font-medium uppercase tracking-wide text-brand-light transition hover:text-white"
          >
            <svg
              xmlns="http://www.w3.org/2000/svg"
              className={`h-3 w-3 transition-transform ${rubricOpen ? "rotate-90" : ""}`}
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
              strokeWidth={2}
            >
              <path strokeLinecap="round" strokeLinejoin="round" d="M9 5l7 7-7 7" />
            </svg>
            Quality Evaluation
          </button>
          {rubricOpen && (
            <div className="mt-2 space-y-2 rounded-xl border border-white/8 bg-white/[0.02] p-3">
              {Object.entries(RUBRIC_LABELS).map(([key, label]) => (
                <RubricRow key={key} label={label} data={rubric[key]} />
              ))}
            </div>
          )}
        </div>
      )}

      {/* Warnings */}
      {resource.warnings?.length > 0 && (
        <div className="mt-3 rounded-lg border border-yellow-500/20 bg-yellow-500/5 px-3 py-2">
          {resource.warnings.map((w, i) => (
            <p key={i} className="text-xs text-yellow-300/80">{w}</p>
          ))}
        </div>
      )}

      {/* Link */}
      {resource.url && (
        <a
          href={resource.url}
          target="_blank"
          rel="noopener noreferrer"
          className="mt-3 inline-flex items-center gap-1 text-sm font-medium text-brand-light transition hover:text-white"
        >
          View resource
          <svg
            xmlns="http://www.w3.org/2000/svg"
            className="h-3.5 w-3.5"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
            strokeWidth={2}
          >
            <path strokeLinecap="round" strokeLinejoin="round" d="M14 3h7m0 0v7m0-7L10 14" />
          </svg>
        </a>
      )}
    </div>
  );
}
