import { useState } from "react";
import axios from "axios";
import Footer from "../components/Footer";
import UploadZone from "../components/UploadZone";
import ResultCard from "../components/ResultCard";
import PDFViewer from "../components/PDFViewer";

export default function Home() {
  const [guidelines, setGuidelines] = useState([]);
  const [isUploadingGuide, setIsUploadingGuide] = useState(false);
  const [guideMessage, setGuideMessage] = useState("");
  const [guideFileName, setGuideFileName] = useState("");

  const [isUploadingContent, setIsUploadingContent] = useState(false);
  const [contentMessage, setContentMessage] = useState("");
  const [contentFileName, setContentFileName] = useState("");
  const [isContentReady, setIsContentReady] = useState(false);

  const [isAuditing, setIsAuditing] = useState(false);
  const [auditProgress, setAuditProgress] = useState(0);
  const [auditResults, setAuditResults] = useState(null);

  const [pdfUrl, setPdfUrl] = useState(null);
  const [isGeneratingPdf, setIsGeneratingPdf] = useState(false);

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
      const res = await axios.post(
        "http://localhost:8000/upload-guidelines",
        formData,
      );
      const formatted = res.data.guidelines.map((rule, i) => ({
        id: i,
        text: rule,
        selected: true,
      }));
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
  const toggleSelection = (id) =>
    setGuidelines((gs) =>
      gs.map((g) => (g.id === id ? { ...g, selected: !g.selected } : g)),
    );
  const updateText = (id, t) =>
    setGuidelines((gs) => gs.map((g) => (g.id === id ? { ...g, text: t } : g)));
  const setAll = (v) =>
    setGuidelines((gs) => gs.map((g) => ({ ...g, selected: v })));

  /* ── Run Audit ── */
  const runAlignmentAudit = async () => {
    const selected = guidelines.filter((g) => g.selected).map((g) => g.text);
    if (!selected.length) {
      alert("Select at least one guideline.");
      return;
    }
    setIsAuditing(true);
    setAuditResults(null);
    setPdfUrl(null);
    setAuditProgress(0);

    // Simulate progressive progress while waiting
    const ticker = setInterval(
      () => setAuditProgress((p) => Math.min(p + 2, 90)),
      300,
    );
    try {
      const res = await axios.post("http://localhost:8000/run-audit", {
        guidelines: selected,
      });
      clearInterval(ticker);
      setAuditProgress(100);
      setAuditResults(res.data.results);

      // Automatically generate PDF after audit
      await generateAuditPdf(selected);
    } catch (err) {
      clearInterval(ticker);
      console.error(err);
      alert("Failed to run audit. Check backend terminal.");
    } finally {
      setIsAuditing(false);
    }
  };

  /* ── Generate PDF ── */
  const generateAuditPdf = async (guidelines) => {
    setIsGeneratingPdf(true);
    try {
      const res = await axios.post(
        "http://localhost:8000/generate-pdf",
        { guidelines },
        { responseType: "blob" },
      );

      // Create a blob URL for the PDF
      const pdfBlob = new Blob([res.data], { type: "application/pdf" });
      const pdfUrl = URL.createObjectURL(pdfBlob);
      setPdfUrl(pdfUrl);

      // Store blob for download
      window.auditPdfBlob = pdfBlob;
    } catch (err) {
      console.error("Failed to generate PDF:", err);
    } finally {
      setIsGeneratingPdf(false);
    }
  };

  /* ── Download PDF ── */
  const handlePdfDownload = () => {
    if (window.auditPdfBlob) {
      const url = URL.createObjectURL(window.auditPdfBlob);
      const a = document.createElement("a");
      a.href = url;
      a.download = "audit_report.pdf";
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    }
  };

  const selectedCount = guidelines.filter((g) => g.selected).length;

  return (
    <div className="min-h-screen flex flex-col bg-[#0e1712] font-sans pl-[20px] pr-[60px] py-5">
      {/* --- NAVBAR --- */}
      <div className="bg-[#0e1712] border-b-1 border-[#262730] pl-[30px] pr-[20px]">
        <div className="max-w-5xl mx-auto flex items-center gap-3">
          <div>
            <h1 className="text-2xl font-bold text-white tracking-[-0.5px]">
              🎓 Parallex:{" "}
              <span className="text-[#c7dbc3]">
                Automated Curriculum Auditor
              </span>
            </h1>
            <p className="text-sm text-white">
              Cross-Document Semantic Analysis System
            </p>
          </div>
        </div>
      </div>

      {/* --- MAIN CONTENT --- */}
      <main className="flex-grow max-w-5xl mx-auto w-full py-8 pl-[32px] pr-[32px]">
        {/* ── Intro ── */}
        <p className="text-white mb-[28px] text-sm">
          Upload your <strong>Guidelines</strong> first — review &amp; select
          the rules you want checked — then upload your{" "}
          <strong>Course Content</strong> and run the audit.
        </p>

        {/* ── Step 1: Guidelines Upload ── */}
        <div className="bg-[#1e3029] border border-[#262730] rounded-[8px] p-[20px]">
          <div className="bg-[#1a3a2a] border-l-[4px] border-l-[#3a645a] rounded-[6px] mb-[12px] px-[16px] py-[12px] text-white font-semibold text-[14px]">
            📋 Step 1: Upload Guidelines{" "}
            <span className="font-[400]">(Syllabus / Standards)</span>
          </div>
          <UploadZone
            label="Drop Guideline PDF"
            onChange={handleGuidelineUpload}
            disabled={isUploadingGuide || auditResults !== null}
            message={guideMessage}
            fileName={guideFileName}
          />
        </div>

        {/* ── Step 2: Review & Select Guidelines ── */}
        {guidelines.length > 0 && (
          <div className="bg-[#1e3029] border border-[#262730] rounded-[8px] p-[20px] mt-[20px]">
            <div className="flex justify-between items-center mb-[12px]">
              <div className="bg-[#1a3a2a] border-l-[4px] border-l-[#3a645a] rounded-[6px] mb-[12px] px-[16px] py-[12px] text-white font-semibold text-[14px]">
                📝 Step 2: Review Guidelines{" "}
                <span className="text-[13px] text-white font-[500]">
                  {selectedCount} / {guidelines.length} selected
                </span>{" "}
              </div>
              <div className="flex gap-[8px]">
                <button
                  onClick={() => setAll(true)}
                  className="bg-[#262730] text-[#cfd1db] border border-[#3d664d] rounded-[6px] px-[16px] py-[6px] text-[12px] cursor-pointer whitespace-nowrap"
                >
                  Select All
                </button>
                <button
                  onClick={() => setAll(false)}
                  className="bg-[#262730] text-[#cfd1db] border border-[#3d664d] rounded-[6px] px-[16px] py-[6px] text-[12px] cursor-pointer whitespace-nowrap"
                >
                  Deselect All
                </button>
              </div>
            </div>

            <div className="max-h-[280px] overflow-y-auto border rounded-[6px] border-[#262730]">
              {guidelines.map((rule, i) => (
                <div
                  key={rule.id}
                  className={`flex items-start gap-[12px] px-[14px] py-[10px] ${
                    i < guidelines.length - 1 ? "border-b border-[#262730]" : ""
                  } ${rule.selected ? "bg-[#1a3a2a]" : "bg-[#0a311e]"}`}
                >
                  <input
                    type="checkbox"
                    checked={rule.selected}
                    onChange={() => toggleSelection(rule.id)}
                    className="mt-[3px]  accent-[#21c45d] cursor-pointer"
                  />
                  <input
                    type="text"
                    value={rule.text}
                    onChange={(e) => updateText(rule.id, e.target.value)}
                    className={`flex-1 bg-transparent border-none outline-none text-[#fafafa] text-[13px] font-inherit ${
                      rule.selected ? "no-underline" : "line-through"
                    }`}
                  />
                </div>
              ))}
            </div>
          </div>
        )}

        {/* ── Step 3: Upload Content (shown after guidelines are loaded) ── */}
        {guidelines.length > 0 && (
          <div className="bg-[#1e3029] border border-[#262730] rounded-[8px] p-[20px] mt-[20px]">
            <div className="bg-[#1a3a2a] border-l-[4px] border-l-[#3a645a] rounded-[6px] mb-[12px] px-[16px] py-[12px] text-white font-semibold text-[14px]">
              📂 Step 3: Upload Course Content{" "}
              <span className="font-normal">(Lecture Notes)</span>
            </div>
            <UploadZone
              label="Drop Lecture PDF"
              onChange={handleContentUpload}
              disabled={isUploadingContent || auditResults !== null}
              message={contentMessage}
              fileName={contentFileName}
            />
          </div>
        )}

        {/* ── Step 4: Run Audit Button ── */}
        {guidelines.length > 0 && isContentReady && (
          <div className="my-[24px] flex justify-center">
            <button
              onClick={runAlignmentAudit}
              disabled={isAuditing || auditResults !== null}
              className="border border-[#3d664d] rounded-[6px] bg-[#0e1712] text-[#cfd1db] px-[32px] py-[12px] font-bold text-[16px] inline-flex items-center gap-[10px] disabled:opacity-70 disabled:cursor-not-allowed"
            >
              {isAuditing ? "🔄 Analysing ..." : "🚀 Check Alignment"}
            </button>
          </div>
        )}

        {/* ── Progress Bar (while auditing) ── */}
        {isAuditing && (
          <div className="h-[4px] bg-[#262730] rounded-[2px] my-[16px]">
            <div
              className="h-full bg-[#748b75] rounded-[2px] transition-all duration-300 ease-in-out"
              style={{ width: `${auditProgress}%` }}
            />
          </div>
        )}

        {/* ── Audit Results ── */}
        {auditResults && (
          <div className="mt-[36px]">
            <div className="border-t border-[#262730] my-[32px]" />
            <p className="text-[#fafafa] text-[22px] font-bold mb-1 flex items-center gap-2">
              <span>📄</span> Analysis
            </p>

            <div className="mt-[16px]">
              {auditResults.map((result, i) => (
                <ResultCard key={i} result={result} index={i} />
              ))}
            </div>
            <p className="text-[#21c45d] font-semibold text-[14px] mt-[16px]">
              ✅ Analysis Complete!
            </p>

            {/* PDF Viewer below results */}
            <PDFViewer
              pdfUrl={pdfUrl}
              isGenerating={isGeneratingPdf}
              onDownload={handlePdfDownload}
            />
          </div>
        )}
      </main>

      <Footer />
    </div>
  );
}
