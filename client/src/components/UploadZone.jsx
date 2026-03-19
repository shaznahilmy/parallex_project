import React from "react";

export default function UploadZone({
  label,
  onChange,
  disabled,
  message,
  fileName,
}) {
  return (
    <div>
      <span className="text-[#f5fbef] font-[13px] mb-[6px] block">{label}</span>
      <label
        className={`bg-[#0e1712] border border-[#3d664d] rounded-[8px] p-[20px] flex items-center justify-between relative transition-colors duration-200 ${
          disabled
            ? "opacity-60 cursor-not-allowed"
            : "opacity-100 cursor-pointer"
        }`}
      >
        <div className="flex items-center gap-[14px]">
          <div className="text-[#4a4f6a] text-[28px]">☁️</div>
          <div>
            <p className="text-[#cfd1db] font-[14px] font-medium m-0">
              {fileName || "Drag and drop file here"}
            </p>
            <p className="text-[#4a4f6a] text-[12px] mt-[2px] mb-0">
              Limit 200MB per file • PDF
            </p>
          </div>
        </div>
        <span className="bg-[#262730] text-[#cfd1db] border border-[#3d664d] rounded-[6px] px-[16px] py-[6px] text-[13px] cursor-pointer whitespace-nowrap">
          {" "}
          Browse files
        </span>
        <input
          type="file"
          accept="application/pdf"
          onChange={onChange}
          disabled={disabled}
          className={`absolute inset-0 opacity-0 ${disabled ? "cursor-not-allowed" : "cursor-pointer"}`}
        />
      </label>
      {message && (
        <p
          className={`text-[13px] mt-[8px] ${
            message.startsWith("✅")
              ? "text-[#21c45d]"
              : message.startsWith("❌")
                ? "text-[#f87171]"
                : "text-[#fafafa]"
          }`}
        >
          {message}
        </p>
      )}
    </div>
  );
}
