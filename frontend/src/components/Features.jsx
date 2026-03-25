// eslint-disable-next-line no-unused-vars
import { motion } from "framer-motion";

const values = [
  {
    title: "Lower Student Costs",
    description:
      "Surface free, high-quality materials so students never face a paywall to learn.",
    icon: (
      <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor" className="h-6 w-6">
        <path strokeLinecap="round" strokeLinejoin="round" d="M12 6v12m-3-2.818.879.659c1.171.879 3.07.879 4.242 0 1.172-.879 1.172-2.303 0-3.182C13.536 12.219 12.768 12 12 12c-.725 0-1.45-.22-2.003-.659-1.106-.879-1.106-2.303 0-3.182s2.9-.879 4.006 0l.415.33M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
      </svg>
    ),
  },
  {
    title: "AI-Curated Results",
    description:
      "Uses structured rubrics and real data to return verified resources, not random web results.",
    icon: (
      <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor" className="h-6 w-6">
        <path strokeLinecap="round" strokeLinejoin="round" d="M9.813 15.904L9 18.75l-.813-2.846a4.5 4.5 0 00-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 003.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 003.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 00-3.09 3.09zM18.259 8.715L18 9.75l-.259-1.035a3.375 3.375 0 00-2.455-2.456L14.25 6l1.036-.259a3.375 3.375 0 002.455-2.456L18 2.25l.259 1.035a3.375 3.375 0 002.455 2.456L21.75 6l-1.036.259a3.375 3.375 0 00-2.455 2.456zM16.894 20.567L16.5 21.75l-.394-1.183a2.25 2.25 0 00-1.423-1.423L13.5 18.75l1.183-.394a2.25 2.25 0 001.423-1.423l.394-1.183.394 1.183a2.25 2.25 0 001.423 1.423l1.183.394-1.183.394a2.25 2.25 0 00-1.423 1.423z" />
      </svg>
    ),
  },
  {
    title: "Faster Discovery",
    description:
      "Automatically scans OER libraries and syllabi to find resources in seconds, not hours.",
    icon: (
      <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor" className="h-6 w-6">
        <path strokeLinecap="round" strokeLinejoin="round" d="M3.75 13.5l10.5-11.25L12 10.5h8.25L9.75 21.75 12 13.5H3.75z" />
      </svg>
    ),
  },
  {
    title: "Fully Personalized",
    description:
      "Tailored recommendations that match your specific course goals and learning outcomes.",
    icon: (
      <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor" className="h-6 w-6">
        <path strokeLinecap="round" strokeLinejoin="round" d="M15.75 6a3.75 3.75 0 11-7.5 0 3.75 3.75 0 017.5 0zM4.501 20.118a7.5 7.5 0 0114.998 0A17.933 17.933 0 0112 21.75c-2.676 0-5.216-.584-7.499-1.632z" />
      </svg>
    ),
  },
];

const features = [
  {
    title: "Smart Search",
    description: "Ask questions in natural language and get curated OER materials that match your curriculum.",
  },
  {
    title: "Course Alignment",
    description: "Resources are evaluated against your specific syllabus and learning outcomes for relevance.",
  },
  {
    title: "Quality Scoring",
    description: "Every resource is scored with a structured rubric so you can trust what you find.",
  },
  {
    title: "Conversational",
    description: "Refine your search through follow-up questions, just like talking to a research librarian.",
  },
  {
    title: "Open Access",
    description: "Every recommended resource is free and openly licensed for educational use.",
  },
  {
    title: "Always Improving",
    description: "The AI learns from interactions to provide increasingly relevant recommendations over time.",
  },
];

const container = {
  hidden: {},
  visible: { transition: { staggerChildren: 0.1 } },
};

const item = {
  hidden: { opacity: 0, y: 24 },
  visible: {
    opacity: 1,
    y: 0,
    transition: { duration: 0.6, ease: "easeOut" },
  },
};

export default function Features() {
  return (
    <section id="features" className="px-6 py-28 lg:px-12">
      <div className="mx-auto max-w-7xl">
        {/* Mission statement */}
        <motion.div
          className="mx-auto mb-24 max-w-4xl text-center"
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, amount: 0.3 }}
          transition={{ duration: 0.7 }}
        >
          <h2 className="font-display text-2xl font-medium leading-relaxed text-slate-700 dark:text-slate-300 md:text-3xl">
            We believe that in a world where textbook costs keep rising,{" "}
            <span className="text-slate-900 dark:text-white">
              an AI-powered approach is key to ensuring every student gets access to quality learning materials.
            </span>
          </h2>
        </motion.div>

        {/* Value cards - 4 columns like Hyer */}
        <motion.div
          className="mb-28 grid gap-6 sm:grid-cols-2 lg:grid-cols-4"
          variants={container}
          initial="hidden"
          whileInView="visible"
          viewport={{ once: true, amount: 0.2 }}
        >
          {values.map((val) => (
            <motion.article
              key={val.title}
              variants={item}
              className="group rounded-2xl border border-border-soft bg-white/60 p-7 transition-all duration-300 hover:-translate-y-1 hover:border-brand/40 hover:shadow-lg hover:shadow-brand/10 dark:bg-white/[0.03] dark:hover:bg-white/[0.05]"
            >
              <div className="mb-5 inline-flex h-12 w-12 items-center justify-center rounded-xl bg-brand/10 text-brand dark:bg-brand/15 dark:text-brand-light">
                {val.icon}
              </div>
              <h3 className="mb-2 text-lg font-semibold text-slate-900 dark:text-white">
                {val.title}
              </h3>
              <p className="text-sm leading-relaxed text-text-muted">
                {val.description}
              </p>
            </motion.article>
          ))}
        </motion.div>

        {/* Section header */}
        <motion.div
          className="mb-4 text-center"
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, amount: 0.3 }}
          transition={{ duration: 0.6 }}
        >
          <p className="mb-3 text-xs font-semibold tracking-[0.25em] text-brand dark:text-brand-light">
            CAPABILITIES
          </p>
          <h2 className="font-display text-3xl font-semibold tracking-tight text-slate-900 dark:text-white md:text-5xl">
            What sets us apart
          </h2>
          <p className="mx-auto mt-4 max-w-xl text-base text-text-muted">
            Designed to give educators the tools they need, faster, and smarter.
          </p>
        </motion.div>

        <br />

        {/* Feature grid - 6 items like Hyer's membership/ownership/CO2 grid */}
        <motion.div
          className="grid gap-6 sm:grid-cols-2 lg:grid-cols-3"
          variants={container}
          initial="hidden"
          whileInView="visible"
          viewport={{ once: true, amount: 0.15 }}
        >
          {features.map((feature) => (
            <motion.article
              key={feature.title}
              variants={item}
              className="group rounded-2xl border border-border-soft bg-white/60 p-8 transition-all duration-300 hover:border-brand/40 hover:shadow-lg hover:shadow-brand/10 dark:bg-white/[0.03] dark:hover:bg-white/[0.05]"
            >
              <h3 className="mb-3 text-lg font-semibold text-slate-900 dark:text-white">
                {feature.title}
              </h3>
              <p className="text-sm leading-relaxed text-text-muted">
                {feature.description}
              </p>
            </motion.article>
          ))}
        </motion.div>
      </div>
    </section>
  );
}
