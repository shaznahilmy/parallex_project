import { useState, useEffect, useRef } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import axios from "axios";
import Footer from "../components/Footer";
import ResultCard from "../components/ResultCard";
import PDFViewer from "../components/PDFViewer";

export default function Results() {
  const location = useLocation();
  const navigate = useNavigate();
  const { guidelines } = location.state || {};
  const [auditResults, setAuditResults] = useState(null);
  const [pdfUrl, setPdfUrl] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);
  const [auditProgress, setAuditProgress] = useState(0);

  // hasRun prevents React StrictMode's double mount in dev which would otherwise run two api calls.
  const hasRun = useRef(false);

  // Run audit and generate PDF on page load
  useEffect(() => {
    if (hasRun.current) return; // Abort the second StrictMode call
    hasRun.current = true;

    if (!guidelines || guidelines.length === 0) {
      navigate("/");
      return;
    }

    let ticker;

    const runAuditAndGeneratePdf = async () => {
      // Simulating progressive progress while running
      ticker = setInterval(
        () => setAuditProgress((p) => Math.min(p + 2, 80)),
        300,
      );

      try {
        const selected = guidelines
          .filter((g) => g.selected)
          .map((g) => g.text);

        // Running audit first
        const auditRes = await axios.post("http://localhost:8000/run-audit", {
          guidelines: selected,
        });

        // Setting audit results
        setAuditResults(auditRes.data.results);
        setAuditProgress(50);

        // Generating the audit PDF
        const pdfRes = await axios.post(
          "http://localhost:8000/generate-pdf",
          { guidelines: selected },
        );

        if (pdfRes.data.status === "error") {
          throw new Error(pdfRes.data.message || "PDF generation failed");
        }

        // Decoding the base64 string
        const b64 = pdfRes.data.pdf_base64;
        const binaryStr = atob(b64);
        const bytes = new Uint8Array(binaryStr.length);
        for (let i = 0; i < binaryStr.length; i++) {
          bytes[i] = binaryStr.charCodeAt(i);
        }
        const pdfBlob = new Blob([bytes], { type: "application/pdf" });
        const pdfUrl = URL.createObjectURL(pdfBlob);
        setPdfUrl(pdfUrl);

        // Keeping the blob on window so the download button can re-use it
        window.auditPdfBlob = pdfBlob;

        clearInterval(ticker);
        setAuditProgress(100);
        setIsLoading(false);
      } catch (err) {
        console.error("Failed to run audit:", err);
        setError("Failed to run audit. Check backend terminal.");
        clearInterval(ticker);
        setIsLoading(false);
      }
    };

    runAuditAndGeneratePdf();

    return () => {
      if (ticker) clearInterval(ticker);
    };
  }, [guidelines, navigate]);

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

  return (
    <div className="min-h-screen flex flex-col bg-[#0e1712] font-sans pl-[20px] pr-[60px] py-5">
      {/* --- NAVBAR --- */}
      <div className="bg-[#0e1712] border-b-1 border-[#262730] pl-[30px] pr-[20px]">
        <div className="max-w-7xl mx-auto flex items-center justify-between">
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
          <button
            onClick={() => navigate("/")}
            className="text-[#cfd1db] border border-[#3d664d] rounded-[6px] px-[16px] py-[8px] text-[12px] cursor-pointer bg-[#0a311e] hover:transparent"
          >
            ← New Audit
          </button>
        </div>
      </div>

      {/* --- MAIN CONTENT --- */}
      <main className="flex-grow w-full py-8 px-[32px]">
        {/* ── Progress Bar (while loading) ── */}
        {isLoading && (
          <div className="max-w-full mx-auto mb-8">
            <p className="text-[#fafafa] text-[20px] pt-[10px] font-medium mb-2 flex items-center gap-2">
              <span className="animate-spin">🔄</span> Running Analysis...
            </p>
            <div className="h-[4px] bg-[#262730] rounded-[2px] overflow-hidden">
              <div
                className="h-full bg-[#748b75] rounded-[2px] transition-all duration-300 ease-in-out"
                style={{ width: `${auditProgress}%` }}
              />
            </div>
          </div>
        )}

        {error && (
          <div className="max-w-7xl mx-auto mb-6">
            <div className="bg-red-900/20 border border-red-700 rounded-[8px] p-[20px]">
              <p className="text-red-400 text-[14px]">{error}</p>
            </div>
          </div>
        )}

        {auditResults && (
          <div className="max-w-full mx-auto flex flex-col h-full">
            <h2 className="text-[#fafafa] text-[22px] font-bold mb-6 flex items-center gap-2">
              <span>✅</span> Analysis Results
            </h2>

            <div className="grid grid-cols-2 gap-[24px] flex-1">
              {/* Results List on the left */}
              <div className="flex flex-col h-full">
                <div className="bg-[#1e3029] border border-[#262730] rounded-[8px] overflow-hidden flex flex-col flex-1">
                  <div className="bg-[#1a3a2a] border-b border-[#262730] px-[20px] py-[16px]">
                    <h3 className="text-[#c7dbc3] text-[14px] font-semibold uppercase tracking-wide">
                      Analysis Results ({auditResults.length})
                    </h3>
                  </div>

                  {/* Results Container */}
                  <div className="bg-[#1a3a2a] overflow-y-auto flex-grow px-[20px] py-[16px]">
                    <div className="space-y-[16px]">
                      {auditResults.map((result, i) => (
                        <ResultCard key={i} result={result} index={i} />
                      ))}
                    </div>
                  </div>
                </div>
              </div>

              {/* PDF Viewer on the right */}
              <div className="flex flex-col h-full">
                <div className="bg-[#1e3029] border border-[#262730] rounded-[8px] overflow-hidden flex flex-col flex-1">
                  <PDFViewer
                    pdfUrl={pdfUrl}
                    isGenerating={isLoading}
                    onDownload={handlePdfDownload}
                  />
                </div>
              </div>
            </div>
          </div>
        )}
      </main>

      <Footer />
    </div>
  );
}
