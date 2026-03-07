import React from 'react';

const styles = {
  label: {
    color: "#8b8fa8",
    fontSize: "13px",
    marginBottom: "6px",
    display: "block",
  },
  uploadZone: {
    backgroundColor: "#0e1117",
    border: "1px solid #3d4166",
    borderRadius: "8px",
    padding: "20px",
    display: "flex",
    alignItems: "center",
    justifyContent: "space-between",
    cursor: "pointer",
    position: "relative",
    transition: "border-color 0.2s",
  },
  browseBtn: {
    backgroundColor: "#262730",
    color: "#cfd1db",
    border: "1px solid #3d4166",
    borderRadius: "6px",
    padding: "6px 16px",
    fontSize: "13px",
    cursor: "pointer",
    whiteSpace: "nowrap",
  },
};

export default function UploadZone({ label, hint, onChange, disabled, message, fileName }) {
  return (
    <div>
      <span style={styles.label}>{label}</span>
      <label style={{ ...styles.uploadZone, opacity: disabled ? 0.6 : 1, cursor: disabled ? "not-allowed" : "pointer" }}>
        <div style={{ display: "flex", alignItems: "center", gap: "14px" }}>
          <div style={{ color: "#4a4f6a", fontSize: "28px" }}>☁️</div>
          <div>
            <p style={{ color: "#cfd1db", fontWeight: 500, fontSize: "14px", margin: 0 }}>
              {fileName || "Drag and drop file here"}
            </p>
            <p style={{ color: "#4a4f6a", fontSize: "12px", margin: "2px 0 0" }}>{hint}</p>
          </div>
        </div>
        <span style={styles.browseBtn}>Browse files</span>
        <input
          type="file"
          accept="application/pdf"
          onChange={onChange}
          disabled={disabled}
          style={{ position: "absolute", inset: 0, opacity: 0, cursor: disabled ? "not-allowed" : "pointer" }}
        />
      </label>
      {message && (
        <p style={{ fontSize: "13px", marginTop: "8px", color: message.startsWith("✅") ? "#21c45d" : message.startsWith("❌") ? "#f87171" : "#4fc3f7" }}>
          {message}
        </p>
      )}
    </div>
  );
}
