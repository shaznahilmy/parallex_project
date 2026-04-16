export default function NavBar() {
  return (
    <div className="bg-[#0e1712] border-b border-[#262730] px-[30px] pb-5">
      <div className="w-full mx-auto flex items-center justify-between gap-[8px]">
        <div className="min-w-0">
          <h1 className="text-2xl md:text-[36px] font-bold text-white tracking-[-0.3px] flex flex-wrap items-center gap-x-[6px] gap-y-[2px]">
            Parallex:
            <span className="text-[#c7dbc3]">
              {" "}
              Automated Curriculum Auditor
            </span>
          </h1>
          <p className="text-sm md:text-xl text-white mt-2">
            Cross-Document Semantic Analysis System
          </p>
        </div>
      </div>
    </div>
  );
}
