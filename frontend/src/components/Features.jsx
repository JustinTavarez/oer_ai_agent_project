// eslint-disable-next-line no-unused-vars
import { motion } from "framer-motion";

const features = [
  {
    title: "Lower student costs",
    description:
      "Use AI to automate evaluation and recommendations for your students.",
    icon: "01",
  },
  {
    title: "Helps instructors find content faster",
    description:
      "Automatically scans syllabi and OER libraries to suggest relevant resources, instead of manual searching for content.",
    icon: "02",
  },
  {
    title: "Gives reliable, evaluated results",
    description:
      "Uses a structured rubric and real data from GGC syllabi and OER librarie from OpenALG to return accurate, verified resources that meet learning outcomes and not just a list of random results from the web.",
    icon: "03",
  },
];

const container = {
  hidden: {},
  visible: {
    transition: {
      staggerChildren: 0.14,
    },
  },
};

const item = {
  hidden: { opacity: 0, y: 28 },
  visible: {
    opacity: 1,
    y: 0,
    transition: { duration: 0.65, ease: "easeOut" },
  },
};

export default function Features() {
  return (
    <section id="features" className="px-6 py-24 md:px-10">
      <div className="mx-auto max-w-6xl">
        <motion.div
          className="mb-12 max-w-2xl space-y-4"
          initial={{ opacity: 0, y: 24 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, amount: 0.3 }}
          transition={{ duration: 0.7 }}
        >
          <p className="text-sm font-medium tracking-[0.16em] text-brand-light">WHY OER AI AGENT</p>
          <h2 className="text-3xl font-semibold tracking-tight text-white md:text-5xl">
            A modern way to discover and use free learning content.
          </h2>
        </motion.div>

        <motion.div
          className="grid gap-6 md:grid-cols-3"
          variants={container}
          initial="hidden"
          whileInView="visible"
          viewport={{ once: true, amount: 0.22 }}
        >
          {features.map((feature) => (
            <motion.article
              key={feature.title}
              variants={item}
              className="group rounded-3xl border border-white/12 bg-white/[0.04] p-7 transition-all duration-300 hover:-translate-y-1 hover:border-brand/60 hover:shadow-2xl hover:shadow-brand/20"
            >
              <span className="mb-5 inline-flex rounded-full border border-white/20 bg-white/5 px-3 py-1 text-xs font-semibold text-slate-200">
                {feature.icon}
              </span>
              <h3 className="mb-3 text-xl font-semibold text-white">{feature.title}</h3>
              <p className="text-sm leading-relaxed text-text-muted">{feature.description}</p>
            </motion.article>
          ))}
        </motion.div>
      </div>
    </section>
  );
}
