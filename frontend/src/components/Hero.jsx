// eslint-disable-next-line no-unused-vars
import { motion } from "framer-motion";
import { Link } from "react-router-dom";
import aiEducationImg from "../assets/AI-in-education.jpeg";

const containerVariants = {
  hidden: {},
  visible: {
    transition: { staggerChildren: 0.18 },
  },
};

const itemVariants = {
  hidden: { opacity: 0, y: 30 },
  visible: {
    opacity: 1,
    y: 0,
    transition: { duration: 0.9, ease: "easeOut" },
  },
};

const imageVariants = {
  hidden: { opacity: 0, x: 60, scale: 0.92 },
  visible: {
    opacity: 1,
    x: 0,
    scale: 1,
    transition: { duration: 1.1, ease: "easeOut", delay: 0.3 },
  },
};

export default function Hero() {
  return (
    <section className="relative flex min-h-screen items-center overflow-hidden px-6 pt-24 pb-16 lg:px-12">
      <div className="pointer-events-none absolute inset-0 -z-10">
        <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_20%_50%,rgba(200,168,85,0.08),transparent_60%)] dark:bg-[radial-gradient(ellipse_at_20%_50%,rgba(200,168,85,0.12),transparent_60%)]" />
        <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_80%_20%,rgba(59,130,246,0.06),transparent_60%)] dark:bg-[radial-gradient(ellipse_at_80%_20%,rgba(59,130,246,0.08),transparent_60%)]" />
        <div className="absolute bottom-0 left-0 right-0 h-px bg-gradient-to-r from-transparent via-border-soft to-transparent" />
      </div>

      <div className="mx-auto grid w-full max-w-7xl items-center gap-12 lg:grid-cols-2 lg:gap-16">
        {/* Left — text content */}
        <motion.div
          variants={containerVariants}
          initial="hidden"
          animate="visible"
        >
          <motion.p
            className="mb-6 text-xs font-semibold tracking-[0.25em] text-brand dark:text-brand-light"
            variants={itemVariants}
          >
            OPEN EDUCATIONAL RESOURCES
          </motion.p>

          <motion.h1
            className="font-display text-5xl font-bold leading-[1.1] tracking-tight text-slate-900 dark:text-white md:text-6xl lg:text-7xl"
            variants={itemVariants}
          >
            AI-Powered{" "}
            <span className="text-gradient-gold">Learning</span>
          </motion.h1>

          <motion.p
            className="mt-8 max-w-xl text-lg leading-relaxed text-slate-600 dark:text-slate-400 md:text-xl"
            variants={itemVariants}
          >
            More access, freedom and choice for educators and students.
          </motion.p>

          <motion.div className="mt-10 flex flex-wrap gap-5" variants={itemVariants}>
            <Link
              to="/chat"
              className="rounded-full bg-brand px-8 py-3.5 text-sm font-semibold tracking-[0.04em] text-white transition-all duration-300 hover:bg-brand-dark hover:shadow-xl hover:shadow-brand/25"
            >
              Start Chatting
            </Link>
            <a
              href="#features"
              className="rounded-full border border-slate-300 px-8 py-3.5 text-sm font-semibold tracking-[0.04em] text-slate-700 transition-all duration-300 hover:border-brand/50 hover:text-brand dark:border-slate-600 dark:text-slate-300 dark:hover:border-brand/50 dark:hover:text-brand-light"
            >
              Explore Features
            </a>
          </motion.div>

        </motion.div>

        {/* Right — image */}
        <motion.div
          className="relative flex items-center justify-center"
          variants={imageVariants}
          initial="hidden"
          animate="visible"
        >
          <div className="relative">
            <div className="pointer-events-none absolute -inset-4 rounded-3xl bg-brand/10 blur-2xl dark:bg-brand/15" />
            <motion.img
              src={aiEducationImg}
              alt="AI in Education"
              className="relative w-full max-w-lg rounded-2xl border border-border-soft shadow-2xl shadow-brand/10 dark:shadow-brand/20"
              animate={{ y: [0, -10, 0] }}
              transition={{
                duration: 6,
                repeat: Infinity,
                ease: "easeInOut",
              }}
            />
          </div>
        </motion.div>
      </div>

      {/* Stats bar — full width below */}
      <motion.div
        className="absolute bottom-12 left-0 right-0 flex justify-center px-6"
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.9, ease: "easeOut", delay: 1 }}
      >
        <ul></ul>
        <div className="flex w-full max-w-4xl items-center justify-evenly py-6">
          <div className="text-center">
            <p className="text-3xl font-bold text-slate-900 dark:text-white">Free</p>
            <p className="mt-1 text-sm text-text-muted">Open Resources</p>
          </div>
          <div className="h-10 w-px bg-border-soft" />
          <div className="text-center">
            <p className="text-3xl font-bold text-slate-900 dark:text-white">AI</p>
            <p className="mt-1 text-sm text-text-muted">Smart Search</p>
          </div>
          <div className="h-10 w-px bg-border-soft" />
          <div className="text-center">
            <p className="text-3xl font-bold text-slate-900 dark:text-white">24/7</p>
            <p className="mt-1 text-sm text-text-muted">Always Available</p>
          </div>
        </div>
      </motion.div>
    </section>
  );
}
