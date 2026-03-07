import { useState } from "react";
import axios from "axios";
import Footer from "../components/footer";
import UploadZone from "../components/UploadZone";
import ResultCard from "../components/ResultCard";

/* ─── Inline style tokens to match Streamlit dark theme ─── */
const S = {
  card: {
    backgroundColor: "#1e2130",
    border: "1px solid #262730",
    borderRadius: "8px",
    padding: "20px",
  },
  infoBox: (color = "#1a3a5c") => ({
    backgroundColor: color,
    borderLeft: `4px solid #4fc3f7`,
    borderRadius: "6px",
    padding: "12px 16px",
    marginBottom: "12px",
    color: "#cfe8ff",
    fontWeight: 600,
    fontSize: "14px",
  }),
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
  primaryBtn: {
    backgroundColor: "#ff4b4b",
    color: "white",
    border: "none",
    borderRadius: "6px",
    padding: "10px 28px",
    fontWeight: 700,
    fontSize: "15px",
    cursor: "pointer",
    display: "inline-flex",
    alignItems: "center",
    gap: "8px",
    transition: "opacity 0.2s",
  },
  auditBtn: {
    backgroundColor: "#ff4b4b",
    color: "white",
    border: "none",
    borderRadius: "6px",
    padding: "12px 32px",
    fontWeight: 700,
    fontSize: "16px",
    cursor: "pointer",
    display: "inline-flex",
    alignItems: "center",
    gap: "10px",
  },
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
  progressTrack: {
    height: "4px",
    backgroundColor: "#262730",
    borderRadius: "2px",
    margin: "16px 0",
  },
  progressBar: (pct) => ({
    height: "100%",
    width: `${pct}%`,
    backgroundColor: "#4fc3f7",
    borderRadius: "2px",
    transition: "width 0.3s ease",
  }),
  divider: {
    borderTop: "1px solid #262730",
    margin: "32px 0",
  },
  sectionTitle: {
    color: "#fafafa",
    fontSize: "22px",
    fontWeight: 700,
    marginBottom: "4px",
    display: "flex",
    alignItems: "center",
    gap: "10px",
  },
};



export default function Home() {
  const [guidelines, setGuidelines]           = useState([]);
  const [isUploadingGuide, setIsUploadingGuide] = useState(false);
  const [guideMessage, setGuideMessage]       = useState("");
  const [guideFileName, setGuideFileName]     = useState("");

  const [isUploadingContent, setIsUploadingContent] = useState(false);
  const [contentMessage, setContentMessage]   = useState("");
  const [contentFileName, setContentFileName] = useState("");
  const [isContentReady, setIsContentReady]   = useState(false);

  const [isAuditing, setIsAuditing]           = useState(false);
  const [auditProgress, setAuditProgress]     = useState(0);
  const [auditResults, setAuditResults]       = useState(null);

  /* ── Uploads ── */
  const handleGuidelineUpload = async (e) => {
    const file = e.target.files[0];
    if (!file) return;
    setGuideFileName(file.name);
    setIsUploadingGuide(true);
    setGuideMessage("⏳ Extracting guidelines...");
    setGuidelines([]);
    setAuditResults(null);
    const formData = new FormData();
    formData.append("file", file);
    try {
      const res = await axios.post("http://localhost:5173/upload-guidelines", formData);
      const formatted = res.data.guidelines.map((rule, i) => ({ id: i, text: rule, selected: true }));
      setGuidelines(formatted);
      setGuideMessage(`✅ Extracted ${res.data.extracted_count} guidelines.`);
    } catch {
      setGuideMessage("❌ Failed to upload guidelines.");
    } finally {
      setIsUploadingGuide(false);
    }
  };

  const handleContentUpload = async (e) => {
    const file = e.target.files[0];
    if (!file) return;
    setContentFileName(file.name);
    setIsUploadingContent(true);
    setContentMessage("⏳ Indexing course content...");
    const formData = new FormData();
    formData.append("file", file);
    try {
      await axios.post("http://localhost:8000/upload-content", formData);
      setIsContentReady(true);
      setContentMessage("✅ Course content indexed and ready!");
    } catch {
      setContentMessage("❌ Failed to process course content.");
    } finally {
      setIsUploadingContent(false);
    }
  };

  /* ── Guideline picker ── */
  const toggleSelection = (id) => setGuidelines(gs => gs.map(g => g.id === id ? { ...g, selected: !g.selected } : g));
  const updateText      = (id, t) => setGuidelines(gs => gs.map(g => g.id === id ? { ...g, text: t } : g));
  const setAll          = (v) => setGuidelines(gs => gs.map(g => ({ ...g, selected: v })));

  /* ── Run Audit ── */
  const runAlignmentAudit = async () => {
    const selected = guidelines.filter(g => g.selected).map(g => g.text);
    if (!selected.length) { alert("Select at least one guideline."); return; }
    setIsAuditing(true);
    setAuditResults(null);
    setAuditProgress(0);

    // Simulate progressive progress while waiting
    const ticker = setInterval(() => setAuditProgress(p => Math.min(p + 2, 90)), 300);
    try {
      const res = await axios.post("http://localhost:8000/run-audit", { guidelines: selected });
      clearInterval(ticker);
      setAuditProgress(100);
      setAuditResults(res.data.results);
    } catch (err) {
      clearInterval(ticker);
      console.error(err);
      alert("Failed to run audit. Check backend terminal.");
    } finally {
      setIsAuditing(false);
    }
  };

  const selectedCount = guidelines.filter(g => g.selected).length;

  return (
    <div className="min-h-screen flex flex-col" style={{ backgroundColor: '#0e1117', fontFamily: "'Source Sans Pro', 'Segoe UI', sans-serif" }}>
      {/* --- NAVBAR --- */}
      <nav style={{ backgroundColor: '#0e1117', borderBottom: '1px solid #262730' }} className="py-5 px-8">
        <div className="max-w-5xl mx-auto flex items-center gap-3">         
          <div>
            <h1 className="text-2xl font-bold" style={{ color: '#fafafa', letterSpacing: '-0.5px' }}>
             🎓 Parallex: <span style={{ color: '#4fc3f7' }}>Automated Curriculum Auditor</span>
            </h1>
            <p className="text-sm" style={{ color: '#8b8fa8' }}>Cross-Document Semantic Analysis System</p>
          </div>
        </div>
      </nav>

      {/* --- MAIN CONTENT --- */}
      <main className="flex-grow max-w-5xl mx-auto w-full px-8 py-8">
        {/* ── Intro ── */}
        <p style={{ color: "#8b8fa8", marginBottom: "28px", fontSize: "14px" }}>
          Upload your <strong style={{ color: "#cfd1db" }}>Guidelines</strong> first — review &amp; select the rules you want checked — then upload your <strong style={{ color: "#cfd1db" }}>Course Content</strong> and run the audit.
        </p>

        {/* ── Step 1: Guidelines Upload ── */}
        <div style={S.card}>
          <div style={S.infoBox()}>📋 Step 1: Upload Guidelines <span style={{ fontWeight: 400 }}>(Syllabus / Standards)</span></div>
          <UploadZone
            label="Drop Guideline PDF"
            onChange={handleGuidelineUpload}
            disabled={isUploadingGuide}
            message={guideMessage}
            fileName={guideFileName}
            hint="Limit 200MB per file • PDF"
          />
        </div>

        {/* ── Step 2: Review & Select Guidelines ── */}
        {guidelines.length > 0 && (
          <div style={{ ...S.card, marginTop: "20px" }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "12px" }}>
              <p style={S.sectionTitle}>
                <span>📝</span> Step 2: Review Guidelines
                <span style={{ fontSize: "13px", color: "#4fc3f7", fontWeight: 400 }}>
                  {selectedCount} / {guidelines.length} selected
                </span>
              </p>
              <div style={{ display: "flex", gap: "8px" }}>
                <button onClick={() => setAll(true)} style={{ ...S.browseBtn, fontSize: "12px" }}>Select All</button>
                <button onClick={() => setAll(false)} style={{ ...S.browseBtn, fontSize: "12px" }}>Deselect All</button>
              </div>
            </div>

            <div style={{ maxHeight: "280px", overflowY: "auto", borderRadius: "6px", border: "1px solid #262730" }}>
              {guidelines.map((rule, i) => (
                <div
                  key={rule.id}
                  style={{
                    display: "flex",
                    alignItems: "flex-start",
                    gap: "12px",
                    padding: "10px 14px",
                    borderBottom: i < guidelines.length - 1 ? "1px solid #262730" : "none",
                    backgroundColor: rule.selected ? "#1e2130" : "#181b27",
                  }}
                >
                  <input
                    type="checkbox"
                    checked={rule.selected}
                    onChange={() => toggleSelection(rule.id)}
                    style={{ marginTop: "3px", accentColor: "#4fc3f7", cursor: "pointer" }}
                  />
                  <input
                    type="text"
                    value={rule.text}
                    onChange={(e) => updateText(rule.id, e.target.value)}
                    style={{
                      flex: 1,
                      background: "transparent",
                      border: "none",
                      outline: "none",
                      color: rule.selected ? "#cfd1db" : "#4a4f6a",
                      fontSize: "13px",
                      textDecoration: rule.selected ? "none" : "line-through",
                      fontFamily: "inherit",
                    }}
                  />
                </div>
              ))}
            </div>
          </div>
        )}

        {/* ── Step 3: Upload Content (shown after guidelines are loaded) ── */}
        {guidelines.length > 0 && (
          <div style={{ ...S.card, marginTop: "20px" }}>
            <div style={S.infoBox("#1a3a2a")}>📂 Step 3: Upload Course Content <span style={{ fontWeight: 400 }}>(Lecture Notes)</span></div>
            <UploadZone
              label="Drop Lecture PDF"
              onChange={handleContentUpload}
              disabled={isUploadingContent}
              message={contentMessage}
              fileName={contentFileName}
              hint="Limit 200MB per file • PDF"
            />
          </div>
        )}

        {/* ── Step 4: Run Audit Button ── */}
        {guidelines.length > 0 && isContentReady && (
          <div style={{ marginTop: "24px" }}>
            <button
              onClick={runAlignmentAudit}
              disabled={isAuditing}
              style={{ ...S.auditBtn, opacity: isAuditing ? 0.7 : 1, cursor: isAuditing ? "not-allowed" : "pointer" }}
            >
              {isAuditing ? "🔄 Analyzing Semantic Alignment..." : "🚀 Check Alignment"}
            </button>
          </div>
        )}

        {/* ── Progress Bar (while auditing) ── */}
        {isAuditing && (
          <div style={S.progressTrack}>
            <div style={S.progressBar(auditProgress)} />
          </div>
        )}

        {/* ── Audit Results ── */}
        {auditResults && (
          <div style={{ marginTop: "36px" }}>
            <div style={S.divider} />
            <p style={S.sectionTitle}><span>📄</span> Analysis</p>
            <div style={S.progressTrack}>
              <div style={S.progressBar(100)} />
            </div>
            <div style={{ marginTop: "16px" }}>
              {auditResults.map((result, i) => (
                <ResultCard key={i} result={result} index={i} />
              ))}
            </div>
            <p style={{ color: "#21c45d", fontWeight: 600, fontSize: "14px", marginTop: "16px" }}>
              ✅ Analysis Complete!
            </p>
          </div>
        )}
      </main>

      <Footer />
    </div>
  );
}