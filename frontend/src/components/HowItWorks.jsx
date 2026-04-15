// eslint-disable-next-line no-unused-vars
import { motion } from "framer-motion";
import { Link } from "react-router-dom";

const services = [
  {
    label: "Conversational",
    title: "Ask & Discover",
    description:
      "Start with a topic, concept, or learning goal in natural language. The AI explores relevant open resources and narrows down the best matches for your curriculum.",
    cta: "Start Chatting",
    to: "/chat",
  },
  {
    label: "Curated",
    title: "Review & Learn",
    description:
      "Review curated materials scored against structured rubrics. Refine your search through follow-up questions and find the perfect fit for your students.",
    cta: "Explore Features",
    to: "/#features",
  },
];

export default function HowItWorks() {
  return (
    <section id="how-it-works" className="px-6 py-28 lg:px-12">
      <div className="mx-auto max-w-7xl">
        <motion.div
          className="mb-16"
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, amount: 0.3 }}
          transition={{ duration: 0.6 }}
        >
          <p className="mb-3 text-xs font-semibold tracking-[0.25em] text-brand dark:text-brand-light">
            HOW IT WORKS
          </p>
          <h2 className="font-display text-3xl font-semibold tracking-tight text-slate-900 dark:text-white md:text-5xl">
            Smart solutions for all your<br className="hidden md:block" /> resource needs
          </h2>
        </motion.div>

        <div className="grid gap-6 md:grid-cols-2">
          {services.map((service, index) => (
            <motion.div
              key={service.title}
              className="group relative overflow-hidden rounded-2xl border border-border-soft bg-white/60 p-10 transition-all duration-500 hover:border-brand/40 hover:shadow-xl hover:shadow-brand/10 dark:bg-white/[0.03] dark:hover:bg-white/[0.05] md:p-12"
              initial={{ opacity: 0, y: 30 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true, amount: 0.3 }}
              transition={{ duration: 0.6, delay: index * 0.15 }}
            >
              <p className="mb-4 text-xs font-semibold tracking-[0.2em] text-brand dark:text-brand-light">
                {service.label.toUpperCase()}
              </p>
              <h3 className="mb-4 font-display text-3xl font-semibold text-slate-900 dark:text-white md:text-4xl">
                {service.title}
              </h3>
              <p className="mb-8 max-w-md text-sm leading-relaxed text-text-muted md:text-base">
                {service.description}
              </p>
              {service.to.startsWith("/") && !service.to.startsWith("/#") ? (
                <Link
                  to={service.to}
                  className="inline-flex items-center gap-2 text-sm font-semibold text-brand transition-colors hover:text-brand-dark dark:text-brand-light dark:hover:text-brand"
                >
                  {service.cta}
                  <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" className="h-4 w-4 transition-transform group-hover:translate-x-1">
                    <path fillRule="evenodd" d="M3 10a.75.75 0 01.75-.75h10.638L10.23 5.29a.75.75 0 111.04-1.08l5.5 5.25a.75.75 0 010 1.08l-5.5 5.25a.75.75 0 11-1.04-1.08l4.158-3.96H3.75A.75.75 0 013 10z" clipRule="evenodd" />
                  </svg>
                </Link>
              ) : (
                <a
                  href={service.to}
                  className="inline-flex items-center gap-2 text-sm font-semibold text-brand transition-colors hover:text-brand-dark dark:text-brand-light dark:hover:text-brand"
                >
                  {service.cta}
                  <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" className="h-4 w-4 transition-transform group-hover:translate-x-1">
                    <path fillRule="evenodd" d="M3 10a.75.75 0 01.75-.75h10.638L10.23 5.29a.75.75 0 111.04-1.08l5.5 5.25a.75.75 0 010 1.08l-5.5 5.25a.75.75 0 11-1.04-1.08l4.158-3.96H3.75A.75.75 0 013 10z" clipRule="evenodd" />
                  </svg>
                </a>
              )}
            </motion.div>
          ))}
        </div>

        {/* Steps row */}
        <motion.div
          className="mt-16 grid gap-6 md:grid-cols-3"
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, amount: 0.2 }}
          transition={{ duration: 0.6, delay: 0.2 }}
        >
          {[
            { num: "01", title: "Ask", desc: "Type your topic or learning goal in natural language." },
            { num: "02", title: "Discover", desc: "AI explores open resources and finds the best matches." },
            { num: "03", title: "Learn", desc: "Review curated materials and refine through conversation." },
          ].map((step) => (
            <div
              key={step.num}
              className="flex items-start gap-5 rounded-2xl border border-border-soft bg-white/40 p-7 dark:bg-white/[0.02]"
            >
              <span className="flex-shrink-0 font-display text-3xl font-bold text-brand/30 dark:text-brand/20">
                {step.num}
              </span>
              <div>
                <h4 className="mb-1 text-lg font-semibold text-slate-900 dark:text-white">{step.title}</h4>
                <p className="text-sm leading-relaxed text-text-muted">{step.desc}</p>
              </div>
            </div>
          ))}
        </motion.div>
      </div>
    </section>
  );
}
