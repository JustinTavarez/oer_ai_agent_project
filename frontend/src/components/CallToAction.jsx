// eslint-disable-next-line no-unused-vars
import { motion } from "framer-motion";
import { Link } from "react-router-dom";

export default function CallToAction() {
  return (
    <section id="get-started" className="px-6 py-24 md:px-10">
      <motion.div
        className="mx-auto max-w-6xl rounded-4xl border border-slate-900/20 bg-gradient-to-r from-brand/82 via-indigo-500/82 to-blue-500/82 p-10 text-center shadow-[0_18px_60px_rgba(30,41,59,0.2)] dark:border-white/15 dark:shadow-[0_20px_70px_rgba(0,0,0,0.5)] md:p-16"
        initial={{ opacity: 0, y: 30 }}
        whileInView={{ opacity: 1, y: 0 }}
        viewport={{ once: true, amount: 0.3 }}
        transition={{ duration: 0.75, ease: "easeOut" }}
      >
        <h2 className="text-3xl font-semibold tracking-tight text-white md:text-5xl">
          Ready to explore smarter with AI?
        </h2>
        <p className="mx-auto mt-5 max-w-2xl text-sm leading-relaxed text-slate-100 md:text-base">
          Click the button below to get started.
        </p>
        <Link
          to="/chat"
          className="animate-pulse-glow mt-8 inline-flex rounded-full bg-white px-6 py-3 text-sm font-semibold text-indigo-700 transition-transform duration-300 hover:scale-105 dark:bg-white dark:text-indigo-700"
        >
          Start chatting
        </Link>
      </motion.div>
    </section>
  );
}
