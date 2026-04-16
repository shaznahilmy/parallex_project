import { useState } from "react";
import { FiChevronDown, FiChevronRight, FiCheck, FiX } from "react-icons/fi";

const statusStyle = (status) => {
  if (status?.includes("Fully Covered"))
    return { color: "#21c45d", label: "Match: Fully Covered" };
  if (status?.includes("Partially Covered"))
    return { color: "#fbbf24", label: "Match: Partially Covered" };
  if (status?.includes("Not Covered"))
    return { color: "#f87171", label: "Match: Not Covered" };
  return { color: "#8b8fa8", label: status };
};

const scoreColor = (score) => {
  if (score >= 70) return "#21c45d";
  if (score >= 40) return "#fbbf24";
  return "#f87171";
};

const scoreLabel = (score) => {
  if (score >= 70) return "Strong";
  if (score >= 40) return "Moderate";
  if (score >= 15) return "Weak";
  return "Not Covered";
};

const inferOriginalVerdict = (finalStatus) => {
  if (finalStatus?.includes("Partially Covered")) return "Fully Covered";
  if (finalStatus?.includes("Not Covered")) return "Partially Covered";
  return null;
};

export default function ResultCard({ result }) {
  const [open, setOpen] = useState(true);
  const [evidenceOpen, setEvidenceOpen] = useState(false);
  const { color, label } = statusStyle(result.match_status);

  const score = result.weighted_nli_score ?? null;
  const rubric = result.rubric ?? null;
  const advVerdict = result.adversary_verdict;
  const advReason = result.adversary_reason;

  const originalVerdict =
    advVerdict === "DOWNGRADED"
      ? inferOriginalVerdict(result.match_status)
      : null;

  return (
    <div className="bg-[#0a311e] border border-[#262730] rounded-[8px] mb-[16px] min-w-0 break-words">
      {/*Header toggle*/}
      <div
        className="bg-[#0a311e] p-[12px_16px] cursor-pointer flex items-center gap-[10px] text-[#cfd1db] font-semibold text-sm user-select-none border-b border-[#061d12]"
        onClick={() => setOpen((o) => !o)}
      >
        {open ? (
          <FiChevronDown className="text-[#f5fbef] shrink-0" size={16} />
        ) : (
          <FiChevronRight className="text-[#f5fbef] shrink-0" size={16} />
        )}
        <span>{result.guideline}</span>
      </div>

      {open && (
        <div className="p-[16px]">
          {/*Coverage verdict*/}
          <p className="font-bold mb-[8px] text-[14px]" style={{ color }}>
            {label}
          </p>

          {/*Adversary badge*/}
          {advVerdict && advVerdict !== "N/A" && (
            <div className="mb-[10px]">
              <span
                className="text-[11px] font-bold px-[8px] py-[3px] rounded-[4px]"
                style={{
                  background: advVerdict === "UPHELD" ? "#052e16" : "#3b1010",
                  color: advVerdict === "UPHELD" ? "#21c45d" : "#f87171",
                  border: `1px solid ${advVerdict === "UPHELD" ? "#166534" : "#7f1d1d"}`,
                }}
              >
                {advVerdict === "UPHELD"
                  ? " Verified by Second Review"
                  : `Revised from ${originalVerdict ?? "higher verdict"}`}
              </span>
            </div>
          )}

          <p className="text-white text-[14px] leading-[1.6] mb-[14px]">
            {result.reasoning}
          </p>

          {/*Coverage Quality Score*/}
          {score !== null && (
            <div className="mb-[14px]">
              <div className="flex items-center justify-between mb-[4px]">
                <span className="text-[#8b8fa8] text-[11px] font-semibold uppercase tracking-wide">
                  Coverage Quality Score
                </span>
                <div className="flex items-center gap-[6px]">
                  <span
                    className="text-[10px] font-bold px-[6px] py-[1px] rounded-[3px]"
                    style={{
                      background:
                        score >= 70
                          ? "#052e16"
                          : score >= 40
                            ? "#3b2a00"
                            : "#3b1010",
                      color:
                        score >= 70
                          ? "#21c45d"
                          : score >= 40
                            ? "#fbbf24"
                            : "#f87171",
                    }}
                  >
                    {scoreLabel(score)}
                  </span>
                  <span
                    className="text-[12px] font-bold"
                    style={{ color: scoreColor(score) }}
                  >
                    {score}%
                  </span>
                </div>
              </div>

              {/* Progress bar */}
              <div className="h-[5px] bg-[#1a3a2a] rounded-full overflow-hidden">
                <div
                  className="h-full rounded-full transition-all duration-500"
                  style={{ width: `${score}%`, background: scoreColor(score) }}
                />
              </div>

              {/* Rubric badges to show the different criterias met */}
              {rubric && (
                <div className="flex gap-[6px] mt-[8px] flex-wrap">
                  {[
                    { key: "concept_mentioned", label: "Concept" },
                    { key: "mechanism_explained", label: "Mechanism" },
                    { key: "example_provided", label: "Example" },
                  ].map(({ key, label: badgeLabel }) => {
                    const met = rubric[key] === 1;
                    return (
                      <span
                        key={key}
                        className="text-[10px] font-semibold px-[7px] py-[2px] rounded-[4px]"
                        style={{
                          background: met ? "#052e16" : "#1a1a2e",
                          color: met ? "#21c45d" : "#4b5563",
                          border: `1px solid ${met ? "#166534" : "#374151"}`,
                        }}
                      >
                        <span className="inline-flex items-center gap-[3px]">
                          {met ? (
                            <FiCheck size={10} className="shrink-0" />
                          ) : (
                            <FiX size={10} className="shrink-0" />
                          )}
                          {badgeLabel}
                        </span>
                      </span>
                    );
                  })}
                </div>
              )}
            </div>
          )}

          {/*Adversary Agent card */}
          {advVerdict && advVerdict !== "N/A" && advReason && (
            <div
              className="rounded-[6px] overflow-hidden mb-[14px] border"
              style={{
                borderColor: advVerdict === "UPHELD" ? "#166534" : "#7f1d1d",
                background: advVerdict === "UPHELD" ? "#061a0e" : "#1c0808",
              }}
            >
              {/*  Adversary Verdict*/}
              <div
                className="flex items-center gap-[8px] px-[14px] py-[9px] border-b"
                style={{
                  borderColor: advVerdict === "UPHELD" ? "#166534" : "#7f1d1d",
                  background: advVerdict === "UPHELD" ? "#052e16" : "#3b1010",
                }}
              >
                <span
                  className="text-[11px] font-bold px-[7px] py-[2px] rounded-[4px]"
                  style={{
                    background: advVerdict === "UPHELD" ? "#166534" : "#7f1d1d",
                    color: advVerdict === "UPHELD" ? "#21c45d" : "#fecaca",
                  }}
                >
                  {advVerdict === "UPHELD" ? "UPHELD" : "DOWNGRADED"}
                </span>
                <span
                  className="text-[13px] font-semibold"
                  style={{
                    color: advVerdict === "UPHELD" ? "#21c45d" : "#fca5a5",
                  }}
                >
                  Review Explanation
                </span>
              </div>
              {/* Explanation  */}
              <p className="text-white text-[14px] leading-[1.6] px-[14px] py-[10px]">
                {advReason}
              </p>
            </div>
          )}

          {/*Source evidence expander*/}
          <div className="border border-[#061d12] rounded-[6px] overflow-hidden">
            <div
              className={`bg-[#0a311e] p-[12px_16px] cursor-pointer flex items-center gap-[10px] text-[#cfd1db] font-semibold text-sm select-none border-b ${
                evidenceOpen ? "border-[#061d12]" : "border-transparent"
              }`}
              onClick={() => setEvidenceOpen((o) => !o)}
            >
              {evidenceOpen ? (
                <FiChevronDown className="text-[#f5fbef] shrink-0" size={16} />
              ) : (
                <FiChevronRight className="text-[#f5fbef] shrink-0" size={16} />
              )}
              <span>View Source Evidence</span>
            </div>
            {evidenceOpen && (
              <div className="p-[14px] bg-[#0a311e]">
                <p className="text-[#6aab86] text-[12px] font-semibold uppercase tracking-wide mb-[8px]">
                  Retrieved Context
                </p>
                <div className="text-[#cfd1db] text-[12px] leading-[1.7] whitespace-pre-wrap bg-[#061a0e] p-[10px] rounded-[4px] border border-[#262730]">
                  {result.evidence_text}
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
