import { useState, useRef } from "react";
import "./App.css";

function App() {
  const [file, setFile] = useState(null);
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const fileInputRef = useRef(null);

  const handleFileChange = (e) => {
    const selected = e.target.files[0];
    if (selected) {
      setFile(selected);
      setResult(null);
      setError(null);
    }
  };

  const handleDrop = (e) => {
    e.preventDefault();
    const dropped = e.dataTransfer.files[0];
    if (dropped) {
      setFile(dropped);
      setResult(null);
      setError(null);
    }
  };

  const handleSubmit = async () => {
    if (!file) return;
    setLoading(true);
    setError(null);
    setResult(null);

    const formData = new FormData();
    formData.append("file", file);

    try {
      const res = await fetch("/api/transcribe", {
        method: "POST",
        body: formData,
      });
      const data = await res.json();
      if (data.error) {
        setError(data.error);
      } else {
        setResult(data);
      }
    } catch (err) {
      setError("Failed to connect to server.");
    } finally {
      setLoading(false);
    }
  };

  const formatTime = (seconds) => {
    const m = Math.floor(seconds / 60);
    const s = Math.floor(seconds % 60);
    return `${m}:${s.toString().padStart(2, "0")}`;
  };

  return (
    <div className="app">
      <h1>Transcription Pipeline</h1>

      <div
        className="dropzone"
        onClick={() => fileInputRef.current.click()}
        onDrop={handleDrop}
        onDragOver={(e) => e.preventDefault()}
      >
        <input
          type="file"
          ref={fileInputRef}
          accept=".wav,.mp3,.m4a,.ogg,.flac,.webm"
          onChange={handleFileChange}
          hidden
        />
        {file ? (
          <p className="file-name">{file.name}</p>
        ) : (
          <p>Drop an audio file here or click to browse</p>
        )}
      </div>

      <button
        className="transcribe-btn"
        onClick={handleSubmit}
        disabled={!file || loading}
      >
        {loading ? "Transcribing..." : "Transcribe"}
      </button>

      {loading && (
        <div className="spinner-container">
          <div className="spinner" />
          <p>Processing audio — this may take a while for large files...</p>
        </div>
      )}

      {error && <p className="error">{error}</p>}

      {result && (
        <div className="result">
          <div className="stats">
            <div className="stat">
              <span className="stat-label">Language</span>
              <span className="stat-value">{result.language}</span>
            </div>
            <div className="stat">
              <span className="stat-label">Words</span>
              <span className="stat-value">{result.word_count}</span>
            </div>
            <div className="stat">
              <span className="stat-label">Segments</span>
              <span className="stat-value">{result.segment_count}</span>
            </div>
            <div className="stat">
              <span className="stat-label">Duration</span>
              <span className="stat-value">{result.pipeline_duration_seconds}s</span>
            </div>
          </div>

          <div className="section">
            <h2>Transcription</h2>
            <p className="text-block">{result.cleaned_text}</p>
          </div>

          {result.metadata?.segments?.length > 0 && (
            <div className="section">
              <h2>Segments</h2>
              <div className="segments">
                {result.metadata.segments.map((seg, i) => (
                  <div key={i} className="segment">
                    <span className="seg-time">
                      {formatTime(seg.start)} - {formatTime(seg.end)}
                    </span>
                    <span className="seg-text">{seg.text}</span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export default App;
