import React from "react";

export default function PDFViewer({ pdfUrl, isGenerating, onDownload }) {
  return (
    <div className=" mt-[32px] bg-[#0e1712] border border-[#262730] rounded-lg p-[20px] font-sans">
      <div className="flex items-center justify-between mb-[16px]">
        <h2 className="text-[#fafafa] text-[18px]  flex items-center gap-[10px] m-0">
          📄 Audit Report PDF
        </h2>

        <button
          className="bg-[#0e1712] text-[#cfd1db] border border-[#3d664d] rounded-lg p-[12px_32px] font-bold text-[16px] cursor-pointer transition-opacity-0.2s inline-flex items-center gap-[10px]"
          onMouseEnter={(e) => (e.target.style.opacity = "0.8")}
          onMouseLeave={(e) => (e.target.style.opacity = "1")}
          onClick={onDownload}
          disabled={!pdfUrl || isGenerating}
        >
          {isGenerating ? "⏳ Generating..." : "⬇️ Download PDF"}
        </button>
      </div>
      <div className=" w-full h-[600px] flex items-center justify-center">
        {isGenerating ? (
          <p className=" text-[#8b8fa8] text-[14px] text-center">
            ⏳ Generating PDF report...
          </p>
        ) : pdfUrl ? (
          <iframe
            src={pdfUrl}
            className="w-full h-full rounded-lg border-none"
            title="Audit Report PDF"
          />
        ) : (
          <p className=" text-[#8b8fa8] text-[14px] text-center">
            Run an audit to generate the PDF report
          </p>
        )}
      </div>
    </div>
  );
}
