import hatImg from "../assets/hat.jpg";

export default function NavBar() {
  return (
    <div className="bg-[#0e1712] border-b border-[#262730] px-[20px] pb-5">
      <div className="w-full mx-auto flex items-center justify-between gap-[8px]">
        <div className="min-w-0">
          <h1 className="text-2xl font-bold text-white tracking-[-0.3px] flex flex-wrap items-center gap-x-[6px] gap-y-[2px]">
            <img
              src={hatImg}
              alt="graduation hat"
              className="w-[42px] h-[42px] object-contain shrink-0"
            />
            Parallex:
            <span className="text-[#c7dbc3]">
              {" "}
              Automated Curriculum Auditor
            </span>
          </h1>
          <p className="text-sm text-white">
            Cross-Document Semantic Analysis System
          </p>
        </div>
      </div>
    </div>
  );
}
