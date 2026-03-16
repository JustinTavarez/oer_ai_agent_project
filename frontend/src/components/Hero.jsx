// eslint-disable-next-line no-unused-vars
import { motion } from "framer-motion";
import heroImg from "../assets/Ai-background.jpeg";

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
      <div className="pointer-events-none absolute inset-0 -z-10 bg-[radial-gradient(circle_at_20%_20%,rgba(170,59,255,0.25),transparent_45%),radial-gradient(circle_at_80%_0%,rgba(59,130,246,0.2),transparent_45%)]" />
      <motion.div
        className="mx-auto grid min-h-[78vh] max-w-6xl items-center gap-14 lg:grid-cols-[1.1fr_0.9fr]"
        variants={containerVariants}
        initial="hidden"
        animate="visible"
      >
        <div className="space-y-7 text-left">
          <motion.p
            className="inline-flex rounded-full border border-white/15 bg-white/5 px-4 py-2 text-xs font-medium tracking-[0.14em] text-slate-100"
            variants={itemVariants}
          >
            OPEN EDUCATIONAL RESOURCES, REIMAGINED
          </motion.p>
          <motion.h1
            className="text-4xl font-semibold leading-tight tracking-tight text-white md:text-6xl"
            variants={itemVariants}
          >
            Discover a New Open Educational Resources using AI.
          </motion.h1>
          <motion.p
            className="max-w-xl text-base leading-relaxed text-slate-300 md:text-lg"
            variants={itemVariants}
          >
            OER AI Agent helps you ask better questions, surface trusted free learning
            materials, and turn search into a guided conversation.
          </motion.p>
          <motion.div className="flex flex-wrap gap-4" variants={itemVariants}>
            <a
              href="#get-started"
              className="rounded-full bg-gradient-to-r from-brand to-indigo-500 px-6 py-3 text-sm font-semibold text-white transition-all duration-300 hover:scale-105 hover:shadow-2xl hover:shadow-brand/40"
            >
              Get Started
            </a>
            <a
              href="#features"
              className="rounded-full border border-white/25 bg-white/5 px-6 py-3 text-sm font-semibold text-white transition-all duration-300 hover:scale-105 hover:bg-white/10"
            >
              Learn More
            </a>
          </motion.div>
        </div>
        <motion.div
          className="relative flex items-center justify-center"
          initial={{ opacity: 0, scale: 0.94 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ duration: 1, ease: "easeOut", delay: 0.2 }}
        >
          <div className="absolute h-72 w-72 rounded-full bg-brand/35 blur-3xl md:h-96 md:w-96" />
          <img
            src={heroImg}
            alt="OER AI Agent visual"
            className="animate-float relative z-10 w-full max-w-md drop-shadow-[0_20px_80px_rgba(170,59,255,0.45)]"
          />
        </motion.div>
      </motion.div>
    </section>
  );
}
