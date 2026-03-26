import { motion } from "framer-motion";
import { useState, useRef, useEffect, useId } from "react";
import { searchResources } from "../services/api";
import StatusIndicator from "./StatusIndicator";
import ResourceCard from "./ResourceCard";
import SearchHistory, { addToHistory } from "./SearchHistory";

const MotionDiv = motion.div;

const COURSES = [
  { value: "", label: "All Courses" },
  { value: "ARTS 1100", label: "ARTS 1100" },
  { value: "ENGL 1101", label: "ENGL 1101" },
  { value: "ENGL 1102", label: "ENGL 1102" },
  { value: "HIST 2111", label: "HIST 2111" },
  { value: "HIST 2112", label: "HIST 2112" },
  { value: "ITEC 1001", label: "ITEC 1001" },
  { value: "BIOL 1101K", label: "BIOL 1101K" },
  { value: "BIOL 1102", label: "BIOL 1102" },
];

const SOURCES = [
  { value: "both", label: "Both" },
  { value: "GGC Syllabi", label: "GGC Syllabi" },
  { value: "Open ALG", label: "Open ALG" },
];

const initialMessages = [
  {
    id: "m1",
    role: "assistant",
    content:
      "Hi! I am your OER AI assistant. Select a course and source, then ask me about a topic to get resource recommendations.",
  },
];

export default function ChatPage() {
  const [messages, setMessages] = useState(initialMessages);
  const [inputValue, setInputValue] = useState("");
  const [isThinking, setIsThinking] = useState(false);
  const [course, setCourse] = useState("");
  const [sourceFilter, setSourceFilter] = useState("both");
  const messagesEndRef = useRef(null);

  const courseId = useId();
  const sourceId = useId();
  const inputId = useId();

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isThinking]);

  const handleSend = async (overridePrompt) => {
    const value = (overridePrompt ?? inputValue).trim();
    if (!value || isThinking) return;

    addToHistory(value);

    const userMessage = {
      id: `u-${Date.now()}`,
      role: "user",
      content: value,
    };

    setMessages((prev) => [...prev, userMessage]);
    setInputValue("");
    setIsThinking(true);

    try {
      const data = await searchResources(value, {
        courseCode: course || undefined,
        source: sourceFilter === "both" ? undefined : sourceFilter,
        grounded: true,
      });

      const newMessages = [];

      if (data.summary) {
        newMessages.push({
          id: `s-${Date.now()}`,
          role: "assistant",
          content: data.summary,
        });
      }

      if (data.results?.length > 0) {
        newMessages.push({
          id: `r-${Date.now()}`,
          role: "results",
          results: data.results,
        });
      } else if (!data.summary) {
        newMessages.push({
          id: `a-${Date.now()}`,
          role: "assistant",
          content: "No matching resources found. Try broadening your query or changing the filters.",
        });
      }

      if (data.warnings?.length > 0) {
        newMessages.push({
          id: `w-${Date.now()}`,
          role: "warning",
          content: data.warnings.join(" "),
        });
      }

      if (data.errors?.length > 0) {
        newMessages.push({
          id: `err-${Date.now()}`,
          role: "error",
          content: data.errors.join(" "),
        });
      }

      setMessages((prev) => [...prev, ...newMessages]);
    } catch (err) {
      setMessages((prev) => [
        ...prev,
        {
          id: `e-${Date.now()}`,
          role: "error",
          content: err.message || "Something went wrong. Please try again.",
        },
      ]);
    } finally {
      setIsThinking(false);
    }
  };

  const handleHistorySelect = (query) => {
    handleSend(query);
  };

  return (
    <section className="relative overflow-hidden px-6 py-14 md:px-10 md:py-16">
      <div className="pointer-events-none absolute inset-0 -z-10 animate-gradient-shift bg-[radial-gradient(circle_at_15%_20%,rgba(170,59,255,0.32),transparent_42%),radial-gradient(circle_at_85%_15%,rgba(59,130,246,0.24),transparent_36%),radial-gradient(circle_at_50%_90%,rgba(129,140,248,0.22),transparent_45%)]" />
      <div className="pointer-events-none absolute -left-14 top-24 h-56 w-56 animate-float rounded-full bg-brand/25 blur-3xl" />
      <div className="pointer-events-none absolute -right-12 bottom-20 h-72 w-72 animate-float rounded-full bg-indigo-500/25 blur-3xl [animation-delay:900ms]" />

      <MotionDiv
        className="mx-auto flex h-[80vh] w-full max-w-5xl flex-col overflow-hidden rounded-4xl border border-white/15 bg-black/35 shadow-[0_30px_90px_rgba(0,0,0,0.45)] backdrop-blur-xl"
        initial={{ opacity: 0, y: 24 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.7, ease: "easeOut" }}
      >
        {/* Header */}
        <div className="flex flex-col gap-3 border-b border-white/10 px-6 py-4">
          <div className="flex items-start justify-between gap-4">
            <div>
              <p className="text-xs font-medium tracking-[0.16em] text-brand-light">
                OER RESOURCE FINDER
              </p>
              <h1 className="mt-1 text-2xl font-semibold text-white md:text-3xl">
                Find open educational resources
              </h1>
            </div>
            <StatusIndicator />
          </div>

          {/* Filters */}
          <div className="flex flex-wrap items-end gap-4">
            <div className="flex flex-col gap-1">
              <label
                htmlFor={courseId}
                className="text-xs font-medium text-text-muted"
              >
                Course
              </label>
              <select
                id={courseId}
                value={course}
                onChange={(e) => setCourse(e.target.value)}
                className="h-9 rounded-lg border border-white/15 bg-white/5 px-3 text-sm text-white outline-none transition focus-visible:border-brand-light focus-visible:ring-2 focus-visible:ring-brand-light/40"
              >
                {COURSES.map((c) => (
                  <option key={c.value} value={c.value} className="bg-surface">
                    {c.label}
                  </option>
                ))}
              </select>
            </div>

            <div className="flex flex-col gap-1">
              <label
                htmlFor={sourceId}
                className="text-xs font-medium text-text-muted"
              >
                Source
              </label>
              <select
                id={sourceId}
                value={sourceFilter}
                onChange={(e) => setSourceFilter(e.target.value)}
                className="h-9 rounded-lg border border-white/15 bg-white/5 px-3 text-sm text-white outline-none transition focus-visible:border-brand-light focus-visible:ring-2 focus-visible:ring-brand-light/40"
              >
                {SOURCES.map((s) => (
                  <option key={s.value} value={s.value} className="bg-surface">
                    {s.label}
                  </option>
                ))}
              </select>
            </div>

            <SearchHistory onSelect={handleHistorySelect} />
          </div>
        </div>

        {/* Messages */}
        <motion.div
          className="flex-1 space-y-4 overflow-y-auto px-5 py-5 md:px-6"
          initial="hidden"
          animate="visible"
          variants={{
            hidden: {},
            visible: { transition: { staggerChildren: 0.08 } },
          }}
        >
          {messages.map((message) => {
            const isUser = message.role === "user";
            const isError = message.role === "error";
            const isWarning = message.role === "warning";

            if (message.role === "results" && message.results?.length > 0) {
              return (
                <motion.div
                  key={message.id}
                  variants={{
                    hidden: { opacity: 0, y: 10 },
                    visible: {
                      opacity: 1,
                      y: 0,
                      transition: { duration: 0.35 },
                    },
                  }}
                  className="flex justify-start"
                >
                  <div className="grid w-full max-w-[95%] gap-3 md:max-w-[90%] lg:grid-cols-2">
                    {message.results.map((res, i) => (
                      <ResourceCard key={res.resource_id || i} resource={res} />
                    ))}
                  </div>
                </motion.div>
              );
            }

            return (
              <motion.div
                key={message.id}
                variants={{
                  hidden: { opacity: 0, y: 10 },
                  visible: {
                    opacity: 1,
                    y: 0,
                    transition: { duration: 0.35 },
                  },
                }}
                className={`flex ${isUser ? "justify-end" : "justify-start"}`}
              >
                <p
                  className={`max-w-[82%] rounded-3xl px-4 py-3 text-sm leading-relaxed md:max-w-[70%] ${
                    isError
                      ? "border border-red-500/30 bg-red-500/10 text-red-300"
                      : isWarning
                        ? "border border-yellow-500/30 bg-yellow-500/10 text-yellow-300"
                        : isUser
                          ? "bg-gradient-to-r from-brand to-indigo-500 text-white"
                          : "border border-white/10 bg-white/[0.05] text-slate-100"
                  }`}
                >
                  {message.content}
                </p>
              </motion.div>
            );
          })}

          {isThinking && (
            <div className="flex justify-start">
              <div className="inline-flex items-center gap-2 rounded-3xl border border-white/10 bg-white/[0.05] px-4 py-3">
                <span className="typing-dot h-2 w-2 rounded-full bg-brand-light" />
                <span className="typing-dot h-2 w-2 rounded-full bg-brand-light [animation-delay:200ms]" />
                <span className="typing-dot h-2 w-2 rounded-full bg-brand-light [animation-delay:400ms]" />
              </div>
            </div>
          )}

          <div ref={messagesEndRef} />
        </motion.div>

        {/* Input */}
        <div className="border-t border-white/10 p-4 md:p-5">
          <form
            className="flex items-center gap-3"
            onSubmit={(event) => {
              event.preventDefault();
              handleSend();
            }}
          >
            <label htmlFor={inputId} className="sr-only">
              Message
            </label>
            <input
              id={inputId}
              type="text"
              value={inputValue}
              onChange={(event) => setInputValue(event.target.value)}
              placeholder="Ask about a subject, course, or learning goal..."
              className="h-12 flex-1 rounded-full border border-white/20 bg-white/5 px-5 text-sm text-white outline-none transition focus-visible:border-brand-light focus-visible:ring-2 focus-visible:ring-brand-light/40"
            />
            <button
              type="submit"
              disabled={!inputValue.trim() || isThinking}
              className="h-12 rounded-full bg-gradient-to-r from-brand to-indigo-500 px-6 text-sm font-semibold text-white transition hover:scale-[1.03] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-light disabled:cursor-not-allowed disabled:opacity-50"
            >
              Search
            </button>
          </form>
        </div>
      </MotionDiv>
    </section>
  );
}
