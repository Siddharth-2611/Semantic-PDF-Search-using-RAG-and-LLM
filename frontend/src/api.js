const BASE = "/api";

function authHeaders(token) {
  return { Authorization: `Bearer ${token}` };
}

async function parseErrorOrJson(res) {
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      detail = body.detail || detail;
    } catch (_) {
      /* ignore */
    }
    throw new Error(typeof detail === "string" ? detail : JSON.stringify(detail));
  }
  if (res.status === 204) return null;
  return res.json();
}

export async function register(email, password) {
  const res = await fetch(`${BASE}/auth/register`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  });
  return parseErrorOrJson(res);
}

export async function verifyEmail(email, code) {
  const res = await fetch(`${BASE}/auth/verify`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, code }),
  });
  return parseErrorOrJson(res);
}

export async function resendVerification(email) {
  const res = await fetch(`${BASE}/auth/resend-verification`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email }),
  });
  return parseErrorOrJson(res);
}

export async function login(email, password) {
  const res = await fetch(`${BASE}/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  });
  return parseErrorOrJson(res);
}

export async function listDocuments(token) {
  const res = await fetch(`${BASE}/documents`, { headers: authHeaders(token) });
  return parseErrorOrJson(res);
}

export async function uploadDocument(token, file) {
  const form = new FormData();
  form.append("file", file);
  const res = await fetch(`${BASE}/documents/upload`, {
    method: "POST",
    headers: authHeaders(token),
    body: form,
  });
  return parseErrorOrJson(res);
}

export async function deleteDocument(token, documentId) {
  const res = await fetch(`${BASE}/documents/${documentId}`, {
    method: "DELETE",
    headers: authHeaders(token),
  });
  return parseErrorOrJson(res);
}

/**
 * Streams a chat answer via Server-Sent Events.
 * Calls onSources(sources) once, then onToken(text) repeatedly, then onDone().
 */
export async function streamChat(token, { query, documentId, topK = 5 }, { onSources, onToken, onDone, onError }) {
  try {
    const res = await fetch(`${BASE}/chat/stream`, {
      method: "POST",
      headers: { "Content-Type": "application/json", ...authHeaders(token) },
      body: JSON.stringify({ query, document_id: documentId || null, top_k: topK }),
    });
    if (!res.ok || !res.body) {
      const body = await res.json().catch(() => ({}));
      throw new Error(body.detail || "Chat request failed");
    }

    const reader = res.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";

    while (true) {
      const { value, done } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });

      const events = buffer.split("\n\n");
      buffer = events.pop(); // last piece may be incomplete

      for (const raw of events) {
        const lines = raw.split("\n");
        const eventLine = lines.find((l) => l.startsWith("event: "));
        const dataLine = lines.find((l) => l.startsWith("data: "));
        if (!eventLine || !dataLine) continue;

        const eventName = eventLine.replace("event: ", "").trim();
        const data = JSON.parse(dataLine.replace("data: ", ""));

        if (eventName === "sources") onSources?.(data);
        else if (eventName === "token") onToken?.(data.text);
        else if (eventName === "done") onDone?.();
      }
    }
  } catch (err) {
    onError?.(err);
  }
}
