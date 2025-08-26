import React, { useState } from "react";
import axios from "axios";

function App() {
  const [url, setUrl] = useState("");
  const [shortUrl, setShortUrl] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError("");
    setShortUrl("");
    setLoading(true);
    try {
  const apiBase = process.env.REACT_APP_API_BASE || "/api";
  const res = await axios.post(`${apiBase}/shorten`, { url });
      setShortUrl(res.data.short_url);
    } catch (err) {
      setError(err.response?.data?.detail || "Error occurred");
    }
    setLoading(false);
  };

  return (
    <div style={{ maxWidth: 400, margin: "100px auto", textAlign: "center" }}>
      <h2>SaferWatch URL Shortener</h2>
      <form onSubmit={handleSubmit}>
        <input
          type="url"
          value={url}
          onChange={e => setUrl(e.target.value)}
          placeholder="Paste your URL here"
          required
          style={{ width: "80%", padding: 8 }}
        />
        <button type="submit" disabled={loading} style={{ marginLeft: 8, padding: 8 }}>
          {loading ? "Shortening..." : "Shorten"}
        </button>
      </form>
      {shortUrl && (
        <div style={{ marginTop: 20 }}>
          <b>Short URL:</b> <a href={shortUrl} target="_blank" rel="noopener noreferrer">{shortUrl}</a>
        </div>
      )}
      {error && <div style={{ color: "red", marginTop: 20 }}>{error}</div>}
    </div>
  );
}

export default App;
