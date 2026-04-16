import {
  FiCheckCircle,
  FiAlertCircle,
  FiLoader,
  FiUploadCloud,
} from "react-icons/fi";

// messageType: "success" | "error" | "loading" | null
export default function UploadZone({
  label,
  onChange,
  disabled,
  message,
  messageType,
  fileName,
}) {
  const statusIcon = () => {
    if (messageType === "success")
      return <FiCheckCircle size={14} className="shrink-0 text-[#21c45d]" />;
    if (messageType === "error")
      return <FiAlertCircle size={14} className="shrink-0 text-[#f87171]" />;
    if (messageType === "loading")
      return (
        <FiLoader size={14} className="shrink-0 text-[#fafafa] animate-spin" />
      );
    return null;
  };

  const msgColor =
    messageType === "success"
      ? "text-[#21c45d]"
      : messageType === "error"
        ? "text-[#f87171]"
        : "text-[#fafafa]";

  return (
    <div>
      <span className="text-[#f5fbef] text-[13px] mb-[6px] block">{label}</span>
      <label
        className={`bg-[#0e1712] border border-[#3d664d] rounded-[8px] p-[14px] sm:p-[20px] flex items-center justify-between flex-wrap gap-[10px] relative transition-colors duration-200 ${
          disabled
            ? "opacity-60 cursor-not-allowed"
            : "opacity-100 cursor-pointer"
        }`}
      >
        <div className="flex items-center gap-[12px] flex-1 min-w-0">
          <FiUploadCloud size={20} className="shrink-0 text-[#3d664d]" />
          <div className="min-w-0">
            <p className="text-[#cfd1db] text-[13px] sm:text-[14px] font-medium m-0 truncate">
              {fileName || "Drag and drop file here"}
            </p>
            <p className="text-[#4a4f6a] text-[11px] sm:text-[12px] mt-[2px] mb-0">
              Max 25 MB (guidelines) · 50 MB (content) • PDF only
            </p>
          </div>
        </div>

        {/* Browse button */}
        <span className="shrink-0 bg-[#262730] text-[#cfd1db] border border-[#3d664d] rounded-[6px] px-[12px] sm:px-[16px] py-[6px] text-[12px] sm:text-[13px] cursor-pointer whitespace-nowrap">
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
          className={`flex items-center gap-[6px] text-[13px] mt-[8px] ${msgColor}`}
        >
          {statusIcon()}
          {message}
        </p>
      )}
    </div>
  );
}
