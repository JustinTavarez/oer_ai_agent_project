// eslint-disable-next-line no-unused-vars
import { motion } from "framer-motion";
import { Link } from "react-router-dom";

const containerVariants = {
  hidden: {},
  visible: {
    transition: {
      staggerChildren: 0.16,
    },
  },
};

const itemVariants = {
  hidden: { opacity: 0, y: 32 },
  visible: {
    opacity: 1,
    y: 0,
    transition: { duration: 0.8, ease: "easeOut" },
  },
};

export default function Hero() {
  return (
    <section id="top" className="relative overflow-hidden px-6 pb-20 pt-24 md:px-10 md:pt-32">
      <div className="pointer-events-none absolute inset-0 -z-10 bg-[radial-gradient(circle_at_20%_20%,rgba(170,59,255,0.18),transparent_45%),radial-gradient(circle_at_80%_0%,rgba(59,130,246,0.14),transparent_45%)] dark:bg-[radial-gradient(circle_at_20%_20%,rgba(170,59,255,0.25),transparent_45%),radial-gradient(circle_at_80%_0%,rgba(59,130,246,0.2),transparent_45%)]" />
      <motion.div
        className="mx-auto flex min-h-[74vh] w-full max-w-4xl items-center justify-center"
        variants={containerVariants}
        initial="hidden"
        animate="visible"
      >
        <div className="w-full space-y-7 rounded-4xl border border-slate-900/12 bg-white/72 px-6 py-10 text-center shadow-[0_16px_50px_rgba(15,23,42,0.14)] backdrop-blur-sm dark:border-white/12 dark:bg-slate-950/40 dark:shadow-[0_18px_60px_rgba(0,0,0,0.5)] md:px-10">
          <motion.p
            className="inline-flex rounded-full border border-slate-900/15 bg-white/65 px-4 py-2 text-xs font-medium tracking-[0.14em] text-slate-700 dark:border-white/15 dark:bg-white/5 dark:text-slate-100"
            variants={itemVariants}
          >
            OPEN EDUCATIONAL RESOURCES, REIMAGINED
          </motion.p>
          <motion.h1
            className="text-4xl font-semibold leading-tight tracking-tight text-slate-900 dark:text-white md:text-6xl"
            variants={itemVariants}
          >
            Discover a New Open Educational Resources using AI.
          </motion.h1>
          <motion.p
            className="mx-auto max-w-2xl text-base leading-relaxed text-slate-700 dark:text-slate-300 md:text-lg"
            variants={itemVariants}
          >
            OER AI Agent helps you ask better questions, surface trusted free learning
            materials, and turn search into a guided conversation.
          </motion.p>
          <motion.div className="flex flex-wrap justify-center gap-4" variants={itemVariants}>
            <Link
              to="/chat"
              className="rounded-full bg-gradient-to-r from-brand to-indigo-500 px-6 py-3 text-sm font-semibold text-white transition-all duration-300 hover:scale-105 hover:shadow-2xl hover:shadow-brand/40"
            >
              Start Chatting Now
            </Link>
            <a
              href="#features"
              className="rounded-full border border-slate-900/20 bg-white/70 px-6 py-3 text-sm font-semibold text-slate-800 transition-all duration-300 hover:scale-105 hover:bg-white dark:border-white/25 dark:bg-white/5 dark:text-white dark:hover:bg-white/10"
            >
              Learn More
            </a>
          </motion.div>
        </div>
      </motion.div>
    </section>
  );
}
