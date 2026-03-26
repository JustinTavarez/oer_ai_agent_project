const API_BASE = import.meta.env.VITE_API_URL || "http://localhost:8000";

export async function sendChatMessage(prompt, { course, sourceFilter } = {}) {
  const res = await fetch(`${API_BASE}/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ prompt, course, source_filter: sourceFilter }),
  });

  if (!res.ok) {
    throw new Error(`API error: ${res.status}`);
  }

  const data = await res.json();
  if (data.error) {
    throw new Error(data.error);
  }

  return data;
}

export async function searchResources(
  query,
  { courseCode, source, topK = 5, grounded = true } = {},
) {
  const res = await fetch(`${API_BASE}/search`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      query,
      course_code: courseCode || undefined,
      source: source || undefined,
      top_k: topK,
      grounded,
    }),
  });

  if (!res.ok) {
    throw new Error(`API error: ${res.status}`);
  }

  return res.json();
}

export async function checkHealth() {
  const res = await fetch(`${API_BASE}/health`);
  if (!res.ok) {
    throw new Error(`Health check failed: ${res.status}`);
  }
  return res.json();
}
