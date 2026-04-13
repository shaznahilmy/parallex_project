import React from "react";
export default function PDFViewer({ pdfUrl, isGenerating, onDownload }) {
  return (
    <div className="flex flex-col h-full min-w-0 bg-[#1e3029] border border-[#262730] rounded-[8px] overflow-hidden">
      <div className="bg-[#1a3a2a] border-b border-[#262730] px-[20px] py-[16px] flex items-center justify-between shrink-0">
        <h3 className="text-[#c7dbc3] text-[14px] font-semibold uppercase tracking-wide m-0">
          Audit Report PDF
        </h3>

        <button
          className="bg-[#0e1712] text-[#cfd1db] border border-[#3d664d] rounded-[6px] px-[16px] py-[8px] text-[12px] font-semibold cursor-pointer hover:bg-[#1a3a2a] transition-colors inline-flex items-center gap-[8px] disabled:opacity-60 disabled:cursor-not-allowed"
          onClick={onDownload}
          disabled={!pdfUrl || isGenerating}
        >
          {isGenerating ? "Generating..." : "Download Report"}
        </button>
      </div>

      {/* PDF container */}
      <div className="flex-1 min-w-0 overflow-hidden">
        <iframe
          src={`${pdfUrl}#toolbar=0&navpanes=0&scrollbar=0`}
          className="w-full h-full border-none"
          title="Audit Report PDF"
        />
      </div>
    </div>
  );
}
