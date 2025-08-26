import React, { useState } from "react";
import axios from "axios";

function App() {
  const [url, setUrl] = useState("");
  const [shortUrl, setShortUrl] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [copied, setCopied] = useState(false);

  // Prefer absolute /api to work under /url-shortner; allow env override
  // CRA: REACT_APP_API_BASE=/api
  // Vite: VITE_API_BASE=/api
  const apiBase =
    (typeof import.meta !== "undefined" && import.meta.env?.VITE_API_BASE) ||
    process.env.REACT_APP_API_BASE ||
    "/api";

  const validateUrl = (raw) => {
    const s = raw.trim();
    try {
      const u = new URL(s);
      // Basic guard: require http/https
      if (!/^https?:$/.test(u.protocol)) return false;
      return true;
    } catch {
      return false;
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError("");
    setShortUrl("");
    setCopied(false);

    const trimmed = url.trim();
    if (!validateUrl(trimmed)) {
      setError("Please enter a valid http(s) URL.");
      return;
    }

    setLoading(true);
    try {
      const res = await axios.post(`${apiBase}/shorten`, { url: trimmed });
      setShortUrl(res.data.short_url);
    } catch (err) {
      const status = err?.response?.status;
      const detail = err?.response?.data?.detail;
      if (status === 429) {
        setError(detail || "Too many requests. Please wait a bit.");
      } else if (detail) {
        setError(detail);
      } else {
        setError("Network or server error. Please try again.");
      }
    } finally {
      setLoading(false);
    }
  };

  const copyToClipboard = async () => {
    if (!shortUrl) return;
    try {
      await navigator.clipboard.writeText(shortUrl);
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    } catch {
      // ignore
    }
  };

  return (
    <div style={{ maxWidth: 520, margin: "100px auto", textAlign: "center" }}>
      <h2>SaferWatch URL Shortener</h2>
      <form onSubmit={handleSubmit} style={{ marginTop: 16 }}>
        <input
          type="url"
          value={url}
          onChange={(e) => setUrl(e.target.value)}
          placeholder="Paste your URL here (https://...)"
          required
          spellCheck="false"
          autoCapitalize="off"
          autoCorrect="off"
          style={{ width: "75%", padding: 10, fontSize: 14 }}
        />
        <button
          type="submit"
          disabled={loading}
          style={{ marginLeft: 8, padding: "10px 14px", fontSize: 14 }}
        >
          {loading ? "Shortening..." : "Shorten"}
        </button>
      </form>

      {shortUrl && (
        <div style={{ marginTop: 20 }}>
          <div style={{ marginBottom: 6 }}>
            <b>Short URL:</b>{" "}
            <a href={shortUrl} target="_blank" rel="noopener noreferrer">
              {shortUrl}
            </a>
          </div>
          <button onClick={copyToClipboard} style={{ padding: "8px 12px" }}>
            {copied ? "Copied!" : "Copy"}
          </button>
        </div>
      )}

      {error && <div style={{ color: "red", marginTop: 20 }}>{error}</div>}

      <div style={{ marginTop: 28, fontSize: 12, opacity: 0.7 }}>
        API: <code>{apiBase}</code>
      </div>
    </div>
  );
}

export default App;