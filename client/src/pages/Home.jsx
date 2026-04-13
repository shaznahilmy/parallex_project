import React from "react";
import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import axios from "axios";
import Footer from "../components/Footer";
import UploadZone from "../components/UploadZone";
import NavBar from "../components/NavBar";
import handwaveImg from "../assets/handwave.png";

export default function Home() {
  const navigate = useNavigate();
  const [guidelines, setGuidelines] = useState([]);
  const [isUploadingGuide, setIsUploadingGuide] = useState(false);
  const [guideMessage, setGuideMessage] = useState("");
  const [guideMessageType, setGuideMessageType] = useState(null);
  const [guideFileName, setGuideFileName] = useState("");

  const [isUploadingContent, setIsUploadingContent] = useState(false);
  const [contentMessage, setContentMessage] = useState("");
  const [contentMessageType, setContentMessageType] = useState(null);
  const [contentFileName, setContentFileName] = useState("");
  const [isContentReady, setIsContentReady] = useState(false);

  // Typing effect state
  const [displayedText, setDisplayedText] = useState("");
  const [currentIndex, setCurrentIndex] = useState(0);
  const typingText = "Hi! Welcome to Parallex";

  useEffect(() => {
    if (currentIndex < typingText.length) {
      const timer = setTimeout(() => {
        setDisplayedText((prev) => prev + typingText[currentIndex]);
        setCurrentIndex((prev) => prev + 1);
      }, 80);

      return () => clearTimeout(timer);
    }
  }, [currentIndex]);

  // Uploading guidelines
  const handleGuidelineUpload = async (e) => {
    const file = e.target.files[0];
    if (!file) return;

    // resetting content if already uploaded
    if (isContentReady || contentFileName) {
      setIsContentReady(false);
      setContentFileName("");
      setContentMessage(
        "Guidelines changed — please re-upload course content.",
      );
      setContentMessageType(null);
    }

    setGuideFileName(file.name);
    setIsUploadingGuide(true);
    setGuideMessage("Extracting guidelines...");
    setGuideMessageType("loading");
    setGuidelines([]);
    const formData = new FormData();
    formData.append("file", file);
    try {
      const res = await axios.post(
        "http://localhost:8000/upload-guidelines",
        formData,
      );
      const formatted = res.data.guidelines.map((rule, i) => ({
        id: i,
        text: rule,
        selected: true,
      }));
      setGuidelines(formatted);
      setGuideMessage(`Extracted ${res.data.extracted_count} guidelines.`);
      setGuideMessageType("success");
    } catch {
      setGuideMessage("Failed to upload guidelines.");
      setGuideMessageType("error");
    } finally {
      setIsUploadingGuide(false);
    }
  };

  const handleContentUpload = async (e) => {
    const file = e.target.files[0];
    if (!file) return;
    setContentFileName(file.name);
    setIsUploadingContent(true);
    setContentMessage("Indexing course content...");
    setContentMessageType("loading");
    const formData = new FormData();
    formData.append("file", file);
    try {
      await axios.post("http://localhost:8000/upload-content", formData);
      setIsContentReady(true);
      setContentMessage("Course content indexed and ready!");
      setContentMessageType("success");
    } catch {
      setContentMessage("Failed to process course content.");
      setContentMessageType("error");
    } finally {
      setIsUploadingContent(false);
    }
  };

  // Guideline picker
  const toggleSelection = (id) =>
    setGuidelines((gs) =>
      gs.map((g) => (g.id === id ? { ...g, selected: !g.selected } : g)),
    );
  const updateText = (id, t) =>
    setGuidelines((gs) => gs.map((g) => (g.id === id ? { ...g, text: t } : g)));
  const setAll = (v) =>
    setGuidelines((gs) => gs.map((g) => ({ ...g, selected: v })));

  // Running Audit
  const runAlignmentAudit = async () => {
    const selected = guidelines.filter((g) => g.selected).map((g) => g.text);
    if (!selected.length) {
      alert("Select at least one guideline.");
      return;
    }

    // Navigating to results page immediately with guidelines
    navigate("/results", {
      state: {
        guidelines,
      },
    });
  };

  const selectedCount = guidelines.filter((g) => g.selected).length;

  return (
    <>
      <div className="min-h-screen flex flex-col bg-[#0e1712] font-sans pr-[60px] pb-[20px] py-5">
        <NavBar />

        <main className="flex-grow  mx-auto w-full py-8 px-[32px] overflow-x-hidden">
          {/*  Typing Effect Header  */}
          <h2 className="text-2xl md:text-[36px] font-bold text-white mb-[4px]">
            {displayedText}
            {currentIndex < typingText.length && (
              <span className="animate-pulse">|</span>
            )}
            {currentIndex >= typingText.length && (
              <img
                src={handwaveImg}
                alt="wave"
                className="inline w-[36px] h-[32px] object-contain align-middle ml-[8px]"
              />
            )}
          </h2>

          <p className="text-white mb-[16px] text-base font-medium">
            Upload your curriculum guidelines and course content to check
            alignment.
          </p>
          <p className="text-white mb-[28px] text-sm">
            Start by uploading your <strong>Guidelines</strong> (Syllabus /
            Standards), review &amp; select the rules you want checked, then
            upload your <strong>Course Content</strong> and click "Check
            Alignment" to run the audit.
          </p>

          {/*  Guidelines Upload  */}
          <div className="bg-[#1e3029] border border-[#262730] rounded-[8px] p-[20px]">
            <div className="bg-[#1a3a2a] border-l-[4px] border-l-[#3a645a] rounded-[6px] mb-[12px] px-[16px] py-[12px] text-white font-semibold text-[14px]">
              Step 1: Upload Guidelines{" "}
              <span className="font-[400]">(Syllabus / Standards)</span>
            </div>
            <UploadZone
              label="Drop Guideline PDF"
              onChange={handleGuidelineUpload}
              disabled={isUploadingGuide}
              message={guideMessage}
              messageType={guideMessageType}
              fileName={guideFileName}
            />
          </div>

          {/*  Selecting Guidelines  */}
          {guidelines.length > 0 && (
            <div className="bg-[#1e3029] border border-[#262730] rounded-[8px] p-[20px] mt-[20px]">
              <div className="bg-[#1a3a2a] border-l-[4px] border-l-[#3a645a] rounded-[6px] mb-[12px] px-[13px] py-[12px] flex items-center gap-[10px]">
                <input
                  type="checkbox"
                  checked={selectedCount === guidelines.length}
                  ref={(el) => {
                    if (el)
                      el.indeterminate =
                        selectedCount > 0 && selectedCount < guidelines.length;
                  }}
                  onChange={(e) => setAll(e.target.checked)}
                  className="accent-[#21c45d] cursor-pointer w-[12px] h-[12px] shrink-0"
                />
                <span className="text-white font-semibold text-[14px]">
                  Step 2: Review Guidelines
                </span>
                <span className="text-[13px] text-white font-[400]  whitespace-nowrap">
                  {selectedCount} / {guidelines.length} selected
                </span>
              </div>

              <div className="max-h-[280px] overflow-y-auto border rounded-[6px] border-[#262730]">
                {guidelines.map((rule, i) => (
                  <div
                    key={rule.id}
                    className={`flex items-start gap-[12px] px-[14px] py-[10px] ${
                      i < guidelines.length - 1
                        ? "border-b border-[#262730]"
                        : ""
                    } ${rule.selected ? "bg-[#1a3a2a]" : "bg-[#0a311e]"}`}
                  >
                    <input
                      type="checkbox"
                      checked={rule.selected}
                      onChange={() => toggleSelection(rule.id)}
                      className="mt-[3px]  accent-[#21c45d] cursor-pointer"
                    />
                    <input
                      type="text"
                      value={rule.text}
                      onChange={(e) => updateText(rule.id, e.target.value)}
                      className={`flex-1 bg-transparent border-none outline-none text-[#fafafa] text-[13px] font-inherit ${
                        rule.selected ? "no-underline" : "line-through"
                      }`}
                    />
                  </div>
                ))}
              </div>
            </div>
          )}

          {guidelines.length > 0 && (
            <div className="bg-[#1e3029] border border-[#262730] rounded-[8px] p-[20px] mt-[20px]">
              <div className="bg-[#1a3a2a] border-l-[4px] border-l-[#3a645a] rounded-[6px] mb-[12px] px-[16px] py-[12px] text-white font-semibold text-[14px]">
                Step 3: Upload Course Content{" "}
                <span className="font-normal">(Lecture Notes)</span>
              </div>
              <UploadZone
                label="Drop Lecture PDF"
                onChange={handleContentUpload}
                disabled={isUploadingContent}
                message={contentMessage}
                messageType={contentMessageType}
                fileName={contentFileName}
              />
            </div>
          )}

          {guidelines.length > 0 && isContentReady && (
            <div className="my-[24px] flex justify-center">
              <button
                onClick={runAlignmentAudit}
                className="border border-[#3d664d] rounded-[6px] bg-[#0e1712] text-[#cfd1db] px-[32px] py-[12px] font-bold text-[16px] inline-flex items-center gap-[10px] hover:bg-[#1a3a2a] transition-colors"
              >
                Check Alignment
              </button>
            </div>
          )}
        </main>
      </div>
      <Footer />
    </>
  );
}
