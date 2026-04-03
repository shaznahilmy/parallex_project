import { useState, useEffect, useRef } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import axios from "axios";
import Footer from "../components/Footer";
import ResultCard from "../components/ResultCard";
import PDFViewer from "../components/PDFViewer";
import NavBar from "../components/NavBar";

export default function Results() {
  const location = useLocation();
  const navigate = useNavigate();
  const { guidelines } = location.state || {};
  const [auditResults, setAuditResults] = useState(null);
  const [pdfUrl, setPdfUrl] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);

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

    const runAuditAndGeneratePdf = async () => {
      try {
        const selected = guidelines
          .filter((g) => g.selected)
          .map((g) => g.text);

        // Single API call to generate pdf and for the audit results
        const pdfRes = await axios.post("http://localhost:8000/generate-pdf", {
          guidelines: selected,
        });

        if (pdfRes.data.status === "error") {
          throw new Error(pdfRes.data.message || "Audit failed");
        }

        // Populating the left panel from the same response
        setAuditResults(pdfRes.data.results);

        // Decoding the base64 PDF and populate the right panel
        const b64 = pdfRes.data.pdf_base64;
        const binaryStr = atob(b64);
        const bytes = new Uint8Array(binaryStr.length);
        for (let i = 0; i < binaryStr.length; i++) {
          bytes[i] = binaryStr.charCodeAt(i);
        }
        const pdfBlob = new Blob([bytes], { type: "application/pdf" });
        const pdfUrl = URL.createObjectURL(pdfBlob);
        setPdfUrl(pdfUrl);

        // Keeping the blob on window so the download button can reuse it
        window.auditPdfBlob = pdfBlob;

        setIsLoading(false);
      } catch (err) {
        console.error("Failed to run audit:", err);
        setError("Failed to run audit. Check backend terminal.");
        setIsLoading(false);
      }
    };

    runAuditAndGeneratePdf();
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
    <>
      <div className="min-h-screen flex flex-col bg-[#0e1712] font-sans py-5">
        <NavBar />

        <main className="flex-grow mx-[16px] py-8">
          {/* yellow is ipad mini, normal and ipad pro is green */}
          {/* <div className="text-white sm:text-red-400 md:text-yellow-400 lg:text-green-400">
            breakpoint test
          </div> */}
          {/*  Progress Bar  */}
          {isLoading && (
            <div className="max-w-full mx-auto mb-8">
              <style>{`
              @keyframes audit-scan {
                0%   { transform: translateX(-100%); }
                100% { transform: translateX(520%); }
              }
            `}</style>
              <p className="text-[#fafafa] text-[20px] pt-[10px] font-medium mb-3 flex items-center gap-2">
                Running Analysis...
              </p>
              <div className="h-[4px] bg-[#262730] rounded-[2px] overflow-hidden relative">
                <div
                  className="absolute h-full bg-[#748b75] rounded-[2px]"
                  style={{
                    width: "20%",
                    animation: "audit-scan 1.8s ease-in-out infinite",
                  }}
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
            <div className="w-full">
              <div className="w-full  mx-auto">
                <div className="flex justify-between items-center mb-6">
                  <h2 className="text-[#fafafa] text-[22px] font-bold">
                    Analysis Results
                  </h2>

                  <button
                    onClick={() => navigate("/")}
                    className="shrink-0 text-[#cfd1db] border border-[#3d664d] rounded-[6px] px-[32px] py-[8px] text-[14px] bg-[#0a311e] font-semibold"
                  >
                    New Audit
                  </button>
                </div>

                <div className="grid grid-cols-1 lg:grid-cols-2 gap-[20px] w-full">
                  {/* Results List on the left */}
                  <div className="flex flex-col h-[500px] lg:h-[600px] min-w-0">
                    <div className="bg-[#1e3029] border border-[#262730] rounded-[8px] overflow-hidden flex flex-col flex-1">
                      <div className="bg-[#1a3a2a] border-b border-[#262730] px-[20px] py-[16px]">
                        <h3 className="text-[#c7dbc3] text-[14px] font-semibold uppercase tracking-wide">
                          Analysis Results ({auditResults.length})
                        </h3>
                      </div>

                      {/* Results Container */}
                      <div className="bg-[#1a3a2a] overflow-y-auto flex-1 px-[20px] py-[16px]">
                        <div className="space-y-[16px]">
                          {auditResults.map((result, i) => (
                            <ResultCard key={i} result={result} index={i} />
                          ))}
                        </div>
                      </div>
                    </div>
                  </div>

                  {/* PDF Viewer on the right */}
                  <div className="flex flex-col h-[500px] lg:h-[600px] min-w-0">
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
            </div>
          )}
        </main>
      </div>

      <Footer />
    </>
  );
}
