// eslint-disable-next-line no-unused-vars
import { motion } from "framer-motion";
import { useState } from "react";

const initialMessages = [
  {
    id: "m1",
    role: "assistant",
    content: "Hi! I am your OER AI assistant. What topic are you learning today?",
  },
];

const quickReplies = [
  "Great choice. I can help you find high-quality open resources for that topic.",
  "Nice topic. Want beginner, intermediate, or advanced learning materials?",
  "I can recommend free courses, videos, and articles based on your goal.",
];

export default function ChatPage() {
  const [messages, setMessages] = useState(initialMessages);
  const [inputValue, setInputValue] = useState("");
  const [isThinking, setIsThinking] = useState(false);

  const handleSend = () => {
    const value = inputValue.trim();
    if (!value || isThinking) return;

    const userMessage = {
      id: `u-${Date.now()}`,
      role: "user",
      content: value,
    };

    setMessages((prev) => [...prev, userMessage]);
    setInputValue("");
    setIsThinking(true);

    window.setTimeout(() => {
      const reply = quickReplies[Math.floor(Math.random() * quickReplies.length)];
      setMessages((prev) => [
        ...prev,
        {
          id: `a-${Date.now()}`,
          role: "assistant",
          content: reply,
        },
      ]);
      setIsThinking(false);
    }, 900);
  };

  return (
    <section className="relative overflow-hidden px-6 py-14 md:px-10 md:py-16">
      <div className="pointer-events-none absolute inset-0 -z-10 animate-gradient-shift bg-[radial-gradient(circle_at_15%_20%,rgba(170,59,255,0.32),transparent_42%),radial-gradient(circle_at_85%_15%,rgba(59,130,246,0.24),transparent_36%),radial-gradient(circle_at_50%_90%,rgba(129,140,248,0.22),transparent_45%)]" />
      <div className="pointer-events-none absolute -left-14 top-24 h-56 w-56 animate-float rounded-full bg-brand/25 blur-3xl" />
      <div className="pointer-events-none absolute -right-12 bottom-20 h-72 w-72 animate-float rounded-full bg-indigo-500/25 blur-3xl [animation-delay:900ms]" />

      <motion.div
        className="mx-auto flex h-[72vh] w-full max-w-5xl flex-col overflow-hidden rounded-4xl border border-white/15 bg-black/35 shadow-[0_30px_90px_rgba(0,0,0,0.45)] backdrop-blur-xl"
        initial={{ opacity: 0, y: 24 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.7, ease: "easeOut" }}
      >
        <div className="border-b border-white/10 px-6 py-4">
          <p className="text-xs font-medium tracking-[0.16em] text-brand-light">AI CHAT</p>
          <h1 className="mt-1 text-2xl font-semibold text-white md:text-3xl">
            Start learning with OER AI Agent
          </h1>
        </div>

        <motion.div
          className="flex-1 space-y-4 overflow-y-auto px-5 py-5 md:px-6"
          initial="hidden"
          animate="visible"
          variants={{
            hidden: {},
            visible: {
              transition: { staggerChildren: 0.08 },
            },
          }}
        >
          {messages.map((message) => {
            const isUser = message.role === "user";
            return (
              <motion.div
                key={message.id}
                variants={{
                  hidden: { opacity: 0, y: 10 },
                  visible: { opacity: 1, y: 0, transition: { duration: 0.35 } },
                }}
                className={`flex ${isUser ? "justify-end" : "justify-start"}`}
              >
                <p
                  className={`max-w-[82%] rounded-3xl px-4 py-3 text-sm leading-relaxed md:max-w-[70%] ${
                    isUser
                      ? "bg-gradient-to-r from-brand to-indigo-500 text-white"
                      : "border border-white/10 bg-white/[0.05] text-slate-100"
                  }`}
                >
                  {message.content}
                </p>
              </motion.div>
            );
          })}

          {isThinking ? (
            <div className="flex justify-start">
              <div className="inline-flex items-center gap-2 rounded-3xl border border-white/10 bg-white/[0.05] px-4 py-3">
                <span className="typing-dot h-2 w-2 rounded-full bg-brand-light" />
                <span className="typing-dot h-2 w-2 rounded-full bg-brand-light [animation-delay:200ms]" />
                <span className="typing-dot h-2 w-2 rounded-full bg-brand-light [animation-delay:400ms]" />
              </div>
            </div>
          ) : null}
        </motion.div>

        <div className="border-t border-white/10 p-4 md:p-5">
          <form
            className="flex items-center gap-3"
            onSubmit={(event) => {
              event.preventDefault();
              handleSend();
            }}
          >
            <input
              type="text"
              value={inputValue}
              onChange={(event) => setInputValue(event.target.value)}
              placeholder="Ask about a subject, course, or learning goal..."
              className="h-12 flex-1 rounded-full border border-white/20 bg-white/5 px-5 text-sm text-white outline-none transition focus:border-brand-light"
            />
            <button
              type="submit"
              disabled={!inputValue.trim() || isThinking}
              className="h-12 rounded-full bg-gradient-to-r from-brand to-indigo-500 px-6 text-sm font-semibold text-white transition hover:scale-[1.03] disabled:cursor-not-allowed disabled:opacity-50"
            >
              Send
            </button>
          </form>
        </div>
      </motion.div>
    </section>
  );
}
