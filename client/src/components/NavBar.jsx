
export default function NavBar () {
    return(
 <div className="bg-[#0e1712] border-b-1 border-[#262730] pl-[30px] pr-[20px]">
        <div className="max-w-7xl mx-auto flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-white tracking-[-0.5px]">
              🎓 Parallex:{" "}
              <span className="text-[#c7dbc3]">
                Automated Curriculum Auditor
              </span>
            </h1>
            <p className="text-sm text-white">
              Cross-Document Semantic Analysis System
            </p>
          </div>
          <button
            onClick={() => navigate("/")}
            className="text-[#cfd1db] border border-[#3d664d] rounded-[6px] px-[16px] py-[8px] text-[12px] cursor-pointer bg-[#0a311e] hover:transparent"
          >
            ← New Audit
          </button>
        </div>
      </div>
    )
 }
