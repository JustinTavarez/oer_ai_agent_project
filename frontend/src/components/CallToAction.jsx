// eslint-disable-next-line no-unused-vars
import { motion } from "framer-motion";
import { Link } from "react-router-dom";

export default function CallToAction() {
  return (
    <section id="get-started" className="px-6 py-24 md:px-10">
      <motion.div
        className="mx-auto max-w-6xl rounded-4xl border border-white/15 bg-gradient-to-r from-brand/70 via-indigo-500/70 to-blue-500/70 p-10 text-center md:p-16"
        initial={{ opacity: 0, y: 30 }}
        whileInView={{ opacity: 1, y: 0 }}
        viewport={{ once: true, amount: 0.3 }}
        transition={{ duration: 0.75, ease: "easeOut" }}
      >
        <h2 className="text-3xl font-semibold tracking-tight text-white md:text-5xl">
          Ready to explore smarter with AI?
        </h2>
        <p className="mx-auto mt-5 max-w-2xl text-sm leading-relaxed text-indigo-100 md:text-base">
          Click the button below to get started.
        </p>
        <Link
          to="/chat"
          className="animate-pulse-glow mt-8 inline-flex rounded-full bg-white px-6 py-3 text-sm font-semibold text-indigo-700 transition-transform duration-300 hover:scale-105"
        >
          Start chatting
        </Link>
      </motion.div>
    </section>
  );
}
