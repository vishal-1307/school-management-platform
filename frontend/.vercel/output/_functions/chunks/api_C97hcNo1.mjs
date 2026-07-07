const API_URL = ("http://localhost:8000").replace(/\/+$/, "");
const DEFAULT_TIMEOUT_MS = 4500;
async function publicGet(path, timeoutMs = DEFAULT_TIMEOUT_MS) {
  try {
    const response = await fetch(`${API_URL}${path}`, {
      signal: AbortSignal.timeout(timeoutMs),
      headers: { Accept: "application/json" }
    });
    if (!response.ok) return null;
    return await response.json();
  } catch {
    return null;
  }
}
async function publicPost(path, body) {
  const response = await fetch(`${API_URL}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json", Accept: "application/json" },
    body: JSON.stringify(body),
    signal: AbortSignal.timeout(15e3)
  });
  if (!response.ok) {
    let detail = `Request failed (${response.status})`;
    try {
      const data = await response.json();
      if (typeof data.detail === "string") detail = data.detail;
    } catch {
    }
    throw new Error(detail);
  }
  return await response.json();
}

export { publicPost as a, publicGet as p };
