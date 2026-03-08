import { Sparkles, Trash2 } from "lucide-react";

interface TerminalHeaderProps {
  onClear: () => void;
}

export function TerminalHeader({ onClear }: TerminalHeaderProps) {
  return (
    <div className="border-b border-white/5 px-6 py-4 flex items-center justify-between bg-[#18181b]/50 backdrop-blur shrink-0">
      <div className="flex items-center gap-3">
        <div className="bg-gradient-to-br from-indigo-500 to-purple-600 p-2 rounded-lg">
          <Sparkles className="w-4 h-4 text-white" />
        </div>
        <div>
          <h2 className="text-sm font-semibold text-white">AI Architect</h2>
          <p className="text-[10px] font-mono text-slate-500 uppercase tracking-widest">
            Data Architecture Intelligence
          </p>
        </div>
      </div>
      <button
        onClick={onClear}
        className="text-slate-600 hover:text-slate-400 transition-colors p-2 rounded-lg hover:bg-white/5"
        title="Clear history"
      >
        <Trash2 className="w-4 h-4" />
      </button>
    </div>
  );
}
