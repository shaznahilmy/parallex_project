import React, { useState } from 'react';

const styles = {
  resultCard: {
    backgroundColor: "#1e2130",
    border: "1px solid #262730",
    borderRadius: "8px",
    marginBottom: "16px",
    overflow: "hidden",
  },
  expanderHeader: {
    backgroundColor: "#262730",
    padding: "12px 16px",
    cursor: "pointer",
    display: "flex",
    alignItems: "center",
    gap: "10px",
    color: "#cfd1db",
    fontWeight: 600,
    fontSize: "14px",
    userSelect: "none",
    borderBottom: "1px solid #3d4166",
  },
};

/* ─── Status colour helper ─── */
const statusStyle = (status) => {
  if (status?.includes("Fully Covered"))    return { color: "#21c45d", label: "Match: Fully Covered" };
  if (status?.includes("Partially Covered")) return { color: "#fbbf24", label: "Match: Partially Covered" };
  if (status?.includes("Not Covered"))      return { color: "#f87171", label: "Match: Not Covered" };
  return { color: "#8b8fa8", label: status };
};

export default function ResultCard({ result }) {
  const [open, setOpen] = useState(true);
  const [evidenceOpen, setEvidenceOpen] = useState(false);
  const { color, label } = statusStyle(result.match_status);

  return (
    <div style={styles.resultCard}>
      {/* Header / expander toggle */}
      <div style={styles.expanderHeader} onClick={() => setOpen(o => !o)}>
        <span style={{ color: "#4fc3f7", fontSize: "12px" }}>{open ? "▼" : "▶"}</span>
        <span>{result.guideline}</span>
      </div>

      {open && (
        <div style={{ padding: "16px" }}>
          <p style={{ color, fontWeight: 700, marginBottom: "12px", fontSize: "14px" }}>{label}</p>
          <p style={{ color: "#cfd1db", fontSize: "14px", fontStyle: "italic", lineHeight: "1.6", marginBottom: "16px" }}>
            {result.reasoning}
          </p>

          {/* Nested Evidence expander */}
          <div style={{ border: "1px solid #3d4166", borderRadius: "6px", overflow: "hidden" }}>
            <div
              style={{ ...styles.expanderHeader, borderBottom: evidenceOpen ? "1px solid #3d4166" : "none" }}
              onClick={() => setEvidenceOpen(o => !o)}
            >
              <span style={{ color: "#4fc3f7", fontSize: "12px" }}>{evidenceOpen ? "▼" : "▶"}</span>
              <span>View Source Evidence</span>
            </div>
            {evidenceOpen && (
              <div style={{ padding: "14px", backgroundColor: "#0e1117" }}>
                {result.exact_quote && (
                  <div style={{ marginBottom: "12px" }}>
                    <p style={{ color: "#8b8fa8", fontSize: "12px", fontWeight: 600, marginBottom: "6px" }}>EXTRACTED QUOTE</p>
                    <p style={{ color: "#4fc3f7", fontStyle: "italic", fontSize: "13px" }}>"{result.exact_quote}"</p>
                  </div>
                )}
                <div>
                  <p style={{ color: "#8b8fa8", fontSize: "12px", fontWeight: 600, marginBottom: "6px" }}>FAISS RETRIEVED CONTEXT</p>
                  <pre style={{
                    color: "#8b8fa8",
                    fontSize: "12px",
                    whiteSpace: "pre-wrap",
                    fontFamily: "'Fira Code', 'Courier New', monospace",
                    backgroundColor: "#1e2130",
                    padding: "10px",
                    borderRadius: "4px",
                    border: "1px solid #262730",
                    lineHeight: "1.5",
                  }}>
                    {result.evidence_text}
                  </pre>
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
