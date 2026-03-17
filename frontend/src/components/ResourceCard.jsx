export default function ResourceCard({ resource }) {
  return (
    <div className="rounded-2xl border border-white/10 bg-white/[0.04] p-4 transition hover:border-white/20">
      <h3 className="text-base font-semibold text-white">
        {resource.title}
      </h3>

      {resource.match_reason && (
        <div className="mt-2">
          <span className="text-xs font-medium uppercase tracking-wide text-brand-light">
            Why it matches
          </span>
          <p className="mt-0.5 text-sm leading-relaxed text-slate-300">
            {resource.match_reason}
          </p>
        </div>
      )}

      <div className="mt-3 flex flex-wrap gap-2">
        {resource.license && (
          <span className="inline-flex items-center rounded-full border border-emerald-500/30 bg-emerald-500/10 px-2.5 py-0.5 text-xs font-medium text-emerald-300">
            {resource.license}
          </span>
        )}
      </div>

      {resource.quality_summary && (
        <div className="mt-3">
          <span className="text-xs font-medium uppercase tracking-wide text-brand-light">
            Quality
          </span>
          <p className="mt-0.5 text-sm leading-relaxed text-slate-300">
            {resource.quality_summary}
          </p>
        </div>
      )}

      {resource.instructor_ideas && (
        <div className="mt-3">
          <span className="text-xs font-medium uppercase tracking-wide text-brand-light">
            Instructor use ideas
          </span>
          <p className="mt-0.5 text-sm leading-relaxed text-slate-300">
            {resource.instructor_ideas}
          </p>
        </div>
      )}

      {resource.source_link && (
        <a
          href={resource.source_link}
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
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              d="M14 3h7m0 0v7m0-7L10 14"
            />
          </svg>
        </a>
      )}
    </div>
  );
}
