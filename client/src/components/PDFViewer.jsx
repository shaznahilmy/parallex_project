export default function PDFViewer({ pdfUrl, isGenerating, onDownload }) {
  return (
    <div className="flex flex-col h-full bg-[#1e3029] border border-[#262730] rounded-[8px] overflow-hidden">
      <div className="bg-[#1a3a2a] border-b border-[#262730] px-[20px] py-[16px] flex items-center justify-between">
        <h3 className="text-[#c7dbc3] text-[14px] font-semibold uppercase tracking-wide m-0">
          📄 Audit Report PDF
        </h3>

        <button
          className="bg-[#0e1712] text-[#cfd1db] border border-[#3d664d] rounded-[6px] px-[16px] py-[8px] text-[12px] cursor-pointer hover:bg-[#1a3a2a] transition-colors inline-flex items-center gap-[8px]"
          onClick={onDownload}
          disabled={!pdfUrl || isGenerating}
        >
          {isGenerating ? "⏳ Generating..." : "⬇️ Download Report"}
        </button>
      </div>
      <div className="flex-grow w-full flex items-center justify-center overflow-hidden">
        <iframe
          src={`${pdfUrl}#toolbar=0`}
          className="w-full h-full border-none"
          title="Audit Report PDF"
        />
      </div>
    </div>
  );
}
