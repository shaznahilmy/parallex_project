import { useState } from "react";
import axios from "axios";
import Layout from "./components/layout";

function App() {
  // --- STATE MANAGEMENT ---
  const [guidelines, setGuidelines] = useState([]);
  const [isUploadingGuide, setIsUploadingGuide] = useState(false);
  const [guideMessage, setGuideMessage] = useState("");

  const [isUploadingContent, setIsUploadingContent] = useState(false);
  const [contentMessage, setContentMessage] = useState("");
  const [isContentReady, setIsContentReady] = useState(false);

  // NEW: Audit States
  const [isAuditing, setIsAuditing] = useState(false);
  const [auditResults, setAuditResults] = useState(null);

  // --- API LOGIC: UPLOADS ---
  const handleGuidelineUpload = async (event) => {
    const file = event.target.files[0];
    if (!file) return;
    setIsUploadingGuide(true);
    setGuideMessage("Extracting guidelines...");
    const formData = new FormData();
    formData.append("file", file);
    try {
      const response = await axios.post("http://localhost:8000/upload-guidelines", formData);
      const formattedGuidelines = response.data.guidelines.map((rule, index) => ({
        id: index, text: rule, selected: true
      }));
      setGuidelines(formattedGuidelines);
      setGuideMessage(`✅ Extracted ${response.data.extracted_count} guidelines.`);
    } catch (error) {
      setGuideMessage("❌ Failed to upload guidelines.");
      console.error(error)
    } finally {
      setIsUploadingGuide(false);
    }
  };

  const handleContentUpload = async (event) => {
    const file = event.target.files[0];
    if (!file) return;
    setIsUploadingContent(true);
    setContentMessage("Indexing course content...");
    const formData = new FormData();
    formData.append("file", file);
    try {
      await axios.post("http://localhost:8000/upload-content", formData);
      setIsContentReady(true);
      setContentMessage("✅ Course content indexed and ready!");
    } catch (error) {
      setContentMessage("❌ Failed to process course content.");
       console.error(error)
    } finally {
      setIsUploadingContent(false);
    }
  };

  // --- GUIDELINE PICKER LOGIC ---
  const toggleSelection = (id) => setGuidelines(guidelines.map(g => g.id === id ? { ...g, selected: !g.selected } : g));
  const updateText = (id, newText) => setGuidelines(guidelines.map(g => g.id === id ? { ...g, text: newText } : g));
  const setAll = (status) => setGuidelines(guidelines.map(g => ({ ...g, selected: status })));

  // --- NEW: API LOGIC: RUN AUDIT ---
  const runAlignmentAudit = async () => {
    // 1. Filter out unchecked boxes and extract just the text strings
    const selectedRules = guidelines.filter(g => g.selected).map(g => g.text);
    
    if (selectedRules.length === 0) {
      alert("Please select at least one guideline to audit.");
      return;
    }

    setIsAuditing(true);
    setAuditResults(null); // Clear previous results

    try {
      // 2. Send the JSON list to FastAPI
      const response = await axios.post("http://localhost:8000/run-audit", {
        guidelines: selectedRules
      });
      
      // 3. Save the results to state to trigger the UI render
      setAuditResults(response.data.results);
      
    } catch (error) {
      console.error("Audit Error:", error);
      alert("Failed to run audit. Check the backend terminal for errors.");
    } finally {
      setIsAuditing(false);
    }
  };

  // Helper function to color-code the status badges
  const getBadgeColor = (status) => {
    if (status.includes("Fully Covered")) return "bg-green-100 text-green-800 border-green-200";
    if (status.includes("Partially Covered")) return "bg-yellow-100 text-yellow-800 border-yellow-200";
    if (status.includes("Not Covered")) return "bg-red-100 text-red-800 border-red-200";
    return "bg-slate-100 text-slate-800 border-slate-200";
  };

  return (
    <Layout>
      <div className="max-w-4xl mx-auto space-y-8">
        
        {/* ... (Upload Zones & Picker remain exactly the same as before) ... */}
        <div className="text-center">
          <h2 className="text-3xl font-bold text-slate-800">Syllabus Ingestion</h2>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {/* Zone 1 */}
          <div className="bg-white p-6 rounded-xl shadow-sm border-2 border-dashed border-slate-300 hover:border-blue-500 relative">
            <div className="text-center flex flex-col items-center">
              <span className="text-4xl mb-3">📋</span><p className="font-medium text-slate-700">1. Upload Guidelines</p>
            </div>
            <input type="file" accept="application/pdf" onChange={handleGuidelineUpload} disabled={isUploadingGuide} className="absolute inset-0 w-full h-full opacity-0 cursor-pointer disabled:cursor-not-allowed" />
            {guideMessage && <p className="text-sm mt-4 text-center text-blue-600 font-medium">{guideMessage}</p>}
          </div>

          {/* Zone 2 */}
          <div className="bg-white p-6 rounded-xl shadow-sm border-2 border-dashed border-slate-300 hover:border-blue-500 relative">
            <div className="text-center flex flex-col items-center">
              <span className="text-4xl mb-3">📚</span><p className="font-medium text-slate-700">2. Upload Course Content</p>
            </div>
            <input type="file" accept="application/pdf" onChange={handleContentUpload} disabled={isUploadingContent} className="absolute inset-0 w-full h-full opacity-0 cursor-pointer disabled:cursor-not-allowed" />
            {contentMessage && <p className="text-sm mt-4 text-center text-blue-600 font-medium">{contentMessage}</p>}
          </div>
        </div>

        {guidelines.length > 0 && (
          <div className="bg-white border border-slate-200 rounded-xl shadow-sm overflow-hidden">
            <div className="bg-slate-50 border-b border-slate-200 px-6 py-4 flex justify-between items-center">
              <h3 className="font-semibold text-slate-800">Step 3: Refine Guidelines</h3>
              <div className="space-x-2">
                <button onClick={() => setAll(true)} className="text-xs bg-slate-200 hover:bg-slate-300 px-3 py-1 rounded">Select All</button>
                <button onClick={() => setAll(false)} className="text-xs bg-slate-200 hover:bg-slate-300 px-3 py-1 rounded">Deselect All</button>
              </div>
            </div>
            <div className="p-2 max-h-64 overflow-y-auto">
              {guidelines.map((rule) => (
                <div key={rule.id} className="flex items-start gap-3 p-3 border-b border-slate-50 last:border-0">
                  <input type="checkbox" checked={rule.selected} onChange={() => toggleSelection(rule.id)} className="mt-1.5 cursor-pointer" />
                  <input type="text" value={rule.text} onChange={(e) => updateText(rule.id, e.target.value)} className={`flex-1 bg-transparent focus:outline-none ${rule.selected ? 'text-slate-800' : 'text-slate-400 line-through'}`} />
                </div>
              ))}
            </div>
          </div>
        )}

        {/* --- NEW: THE ACTION BUTTON --- */}
        {guidelines.length > 0 && isContentReady && (
          <div className="text-center py-4">
            <button 
              onClick={runAlignmentAudit} 
              disabled={isAuditing}
              className="bg-blue-600 hover:bg-blue-700 disabled:bg-slate-400 text-white font-bold py-4 px-10 rounded-full shadow-lg hover:shadow-xl transition-all text-lg flex items-center justify-center mx-auto gap-3"
            >
              {isAuditing ? (
                <span className="animate-pulse">🔄 Analyzing Semantic Alignment...</span>
              ) : (
                "🚀 Run Constructive Alignment Audit"
              )}
            </button>
          </div>
        )}

        {/* --- NEW: THE AUDIT REPORT UI --- */}
        {auditResults && (
          <div className="mt-12 space-y-6">
            <div className="border-b border-slate-200 pb-4">
              <h2 className="text-3xl font-bold text-slate-800">Audit Report</h2>
              <p className="text-slate-500 mt-1">Source-Grounded Semantic Verification complete.</p>
            </div>

            {auditResults.map((result, index) => (
              <div key={index} className="bg-white border border-slate-200 rounded-xl shadow-sm overflow-hidden">
                <div className="p-6">
                  <div className="flex justify-between items-start gap-4 mb-4">
                    <h4 className="font-semibold text-lg text-slate-800 flex-1">{result.guideline}</h4>
                    <span className={`px-4 py-1.5 rounded-full border text-sm font-bold whitespace-nowrap ${getBadgeColor(result.match_status)}`}>
                      {result.match_status}
                    </span>
                  </div>
                  
                  <p className="text-slate-600 mb-4">{result.reasoning}</p>
                  
                  {/* Evidence Accordion using standard HTML details/summary */}
                  <details className="group border border-slate-200 rounded-lg">
                    <summary className="px-4 py-3 cursor-pointer bg-slate-50 font-medium text-sm text-slate-700 hover:bg-slate-100">
                      View Source Evidence & Quotes
                    </summary>
                    <div className="p-4 bg-white text-sm border-t border-slate-200">
                      <div className="mb-3">
                        <strong className="text-slate-800 block mb-1">Extracted Quote:</strong>
                        <em className="text-blue-700 bg-blue-50 px-2 py-1 rounded">"{result.exact_quote}"</em>
                      </div>
                      <div>
                        <strong className="text-slate-800 block mb-1">FAISS Retrieved Context:</strong>
                        <p className="text-slate-500 whitespace-pre-wrap font-mono text-xs p-3 bg-slate-50 rounded border border-slate-100">
                          {result.evidence_text}
                        </p>
                      </div>
                    </div>
                  </details>
                </div>
              </div>
            ))}
          </div>
        )}

      </div>
    </Layout>
  );
}

export default App;