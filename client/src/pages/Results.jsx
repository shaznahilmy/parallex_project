import { useState, useEffect } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import axios from "axios";
import Footer from "../components/Footer";
import ResultCard from "../components/ResultCard";
import PDFViewer from "../components/PDFViewer";

export default function Results() {
  const location = useLocation();
  const navigate = useNavigate();
  const { guidelines, auditResults } = location.state || {};
  const [pdfUrl, setPdfUrl] = useState(null);
  const [isGeneratingPdf, setIsGeneratingPdf] = useState(true);
  const [error, setError] = useState(null);
  const [auditProgress, setAuditProgress] = useState(0);

  // Generate PDF on page load
  useEffect(() => {
    if (!auditResults || !guidelines) {
      navigate("/");
      return;
    }

    // Simulate progressive progress while generating
    const ticker = setInterval(
      () => setAuditProgress((p) => Math.min(p + 2, 90)),
      300,
    );

    const generatePdf = async () => {
      try {
        const selected = guidelines
          .filter((g) => g.selected)
          .map((g) => g.text);
        const res = await axios.post(
          "http://localhost:8000/generate-pdf",
          { guidelines: selected },
          { responseType: "blob" },
        );

        // Create a blob URL for the PDF
        const pdfBlob = new Blob([res.data], { type: "application/pdf" });
        const pdfUrl = URL.createObjectURL(pdfBlob);
        setPdfUrl(pdfUrl);

        // Store blob for download
        window.auditPdfBlob = pdfBlob;
        clearInterval(ticker);
        setAuditProgress(100);
        setIsGeneratingPdf(false);
      } catch (err) {
        console.error("Failed to generate PDF:", err);
        setError("Failed to generate PDF report.");
        clearInterval(ticker);
        setIsGeneratingPdf(false);
      }
    };

    generatePdf();

    return () => clearInterval(ticker);
  }, [guidelines, auditResults, navigate]);

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
        {/* ── Progress Bar (while generating) ── */}
        {isGeneratingPdf && (
          <div className="max-w-full mx-auto mb-8">
            <p className="text-[#fafafa] text-[14px] font-medium mb-2 flex items-center gap-2">
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
          <div className="max-w-full mx-auto">
            <h2 className="text-[#fafafa] text-[22px] font-bold mb-6 flex items-center gap-2">
              <span>✅</span> Analysis Results
            </h2>

            <div className="grid grid-cols-2 gap-[24px]">
              {/* Results List on the left */}
              <div className="flex flex-col">
                <div className="bg-[#1e3029] border border-[#262730] rounded-[8px] overflow-hidden flex flex-col h-[calc(100vh-280px)]">
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
              <div className="flex flex-col">
                <div className="bg-[#1e3029] border border-[#262730] rounded-[8px] overflow-hidden flex flex-col h-[calc(100vh-280px)]">
                  <PDFViewer
                    pdfUrl={pdfUrl}
                    isGenerating={isGeneratingPdf}
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
