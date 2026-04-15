// eslint-disable-next-line no-unused-vars
import { motion } from "framer-motion";
import { Link } from "react-router-dom";

export default function CallToAction() {
  return (
    <section id="get-started" className="px-6 py-28 lg:px-12">
      <motion.div
        className="relative mx-auto max-w-7xl overflow-hidden rounded-3xl border border-brand/20 bg-gradient-to-br from-brand/10 via-brand/5 to-transparent px-8 py-20 text-center dark:from-brand/15 dark:via-brand/5 md:px-16 md:py-28"
        initial={{ opacity: 0, y: 30 }}
        whileInView={{ opacity: 1, y: 0 }}
        viewport={{ once: true, amount: 0.3 }}
        transition={{ duration: 0.75, ease: "easeOut" }}
      >
        <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(ellipse_at_center,rgba(200,168,85,0.12),transparent_70%)]" />

        <div className="relative">
          <p className="mb-4 text-xs font-semibold tracking-[0.25em] text-brand dark:text-brand-light">
            GET STARTED
          </p>
          <h2 className="font-display text-3xl font-semibold tracking-tight text-slate-900 dark:text-white md:text-5xl lg:text-6xl">
            What are you waiting for?
          </h2>
          <p className="mx-auto mt-6 max-w-xl text-base leading-relaxed text-text-muted md:text-lg">
            Start discovering high-quality, free learning materials powered by AI.
            Your students deserve accessible education.
          </p>
          <Link
            to="/chat"
            className="animate-pulse-glow mt-10 inline-flex rounded-full bg-brand px-8 py-4 text-sm font-semibold tracking-[0.04em] text-white transition-all duration-300 hover:bg-brand-dark hover:shadow-xl"
          >
            Start Chatting Now
          </Link>
        </div>
      </motion.div>
    </section>
  );
}
