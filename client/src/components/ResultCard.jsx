import React, { useState } from "react";

// Status colour helper function to determine the colour and label based on match status
const statusStyle = (status) => {
  if (status?.includes("Fully Covered"))
    return { color: "#21c45d", label: "Match: Fully Covered" };
  if (status?.includes("Partially Covered"))
    return { color: "#fbbf24", label: "Match: Partially Covered" };
  if (status?.includes("Not Covered"))
    return { color: "#f87171", label: "Match: Not Covered" };
  return { color: "#8b8fa8", label: status };
};

export default function ResultCard({ result }) {
  const [open, setOpen] = useState(true);
  const [evidenceOpen, setEvidenceOpen] = useState(false);
  const { color, label } = statusStyle(result.match_status);

  return (
    <div className="bg-[#0a311e] border border-[#262730] rounded-[8px] mb-[16px] overflow-hidden">
      {/*expander toggle */}
      <div
        className="bg-[#0a311e] p-[12px_16px] cursor-pointer flex items-center gap-[10px] text-[#cfd1db] font-semibold text-sm user-select-none border-b border-[#061d12]"
        onClick={() => setOpen((o) => !o)}
      >
        <span className="text-[#f5fbef] text-[12px]">{open ? "▼" : "▶"}</span>
        <span>{result.guideline}</span>
      </div>

      {open && (
        <div className="p-[16px]">
          <p className={`text-[${color}] font-bold mb-[12px] text-[14px]`}>
            {label}
          </p>
          <p className="text-[#cfd1db] text-[14px] italic leading-[1.6] mb-[16px]">
            {result.reasoning}
          </p>

          {/* Nested Evidence expander */}
          <div className="border border-[#061d12] rounded-[6px] overflow-hidden">
            <div
              className={`bg-[#0a311e] p-[12px_16px] cursor-pointer flex items-center gap-[10px] text-[#cfd1db] font-semibold text-sm select-none border-b ${
                evidenceOpen ? "border-[#061d12]" : "border-transparent"
              }`}
              onClick={() => setEvidenceOpen((o) => !o)}
            >
              <span className="text-[#f5fbef] text-[12px]">
                {evidenceOpen ? "▼" : "▶"}
              </span>
              <span>View Source Evidence</span>
            </div>
            {evidenceOpen && (
              <div className="p-[14px] bg-[#0a311e]">
                <div>
                  <p className="text-[#8b8fa8] font-semibold mb-[6px] text-[12px]">
                    RETRIEVED CONTEXT
                  </p>
                  <pre className="text-[#8b8fa8] text-[12px] leading-[1.4] whitespace-pre-wrap font-mono bg-[#1e2130] p-[10px] rounded-[4px] border border-[#262730]">
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
