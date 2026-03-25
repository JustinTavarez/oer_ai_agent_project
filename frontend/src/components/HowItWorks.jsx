// eslint-disable-next-line no-unused-vars
import { motion } from "framer-motion";

const steps = [
  {
    step: "Step 01",
    title: "Ask",
    description: "Start with a topic, concept, or learning goal in natural language.",
  },
  {
    step: "Step 02",
    title: "Search for resources",
    description: "The AI explores relevant open resources and narrows down the best matches.",
  },
  {
    step: "Step 03",
    title: "Learn",
    description: "Review curated materials and keep refining through conversations.",
  },
];

export default function HowItWorks() {
  return (
    <section id="how-it-works" className="px-6 py-24 md:px-10">
      <div className="mx-auto max-w-6xl rounded-4xl border border-slate-900/12 bg-white/70 p-6 shadow-[0_16px_50px_rgba(15,23,42,0.12)] backdrop-blur-sm dark:border-white/12 dark:bg-slate-950/36 dark:shadow-[0_18px_60px_rgba(0,0,0,0.42)] md:p-10">
        <motion.div
          className="mb-12 max-w-2xl space-y-4"
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, amount: 0.3 }}
          transition={{ duration: 0.6 }}
        >
          <p className="text-sm font-medium tracking-[0.16em] text-brand dark:text-brand-light">HOW IT WORKS</p>
          <h2 className="text-3xl font-semibold tracking-tight text-slate-900 dark:text-white md:text-5xl">
            From question to learning path in three steps.
          </h2>
        </motion.div>

        <div className="grid gap-6 md:grid-cols-3">
          {steps.map((step, index) => (
            <motion.div
              key={step.title}
              className="rounded-3xl border border-slate-900/12 bg-gradient-to-b from-white/80 to-slate-100/80 p-7 dark:border-white/12 dark:from-white/[0.08] dark:to-white/[0.02]"
              initial={{ opacity: 0, x: -24 }}
              whileInView={{ opacity: 1, x: 0 }}
              viewport={{ once: true, amount: 0.3 }}
              transition={{ duration: 0.55, delay: index * 0.16, ease: "easeOut" }}
            >
              <div className="mb-5 flex h-11 w-11 items-center justify-center rounded-full bg-brand/20 text-sm font-semibold text-brand dark:bg-brand/25 dark:text-brand-light">
                {index + 1}
              </div>
              <p className="mb-2 text-xs font-medium uppercase tracking-[0.14em] text-slate-500 dark:text-slate-300">
                {step.step}
              </p>
              <h3 className="mb-3 text-2xl font-semibold text-slate-900 dark:text-white">{step.title}</h3>
              <p className="text-sm leading-relaxed text-text-muted">{step.description}</p>
            </motion.div>
          ))}
        </div>
      </div>
    </section>
  );
}
