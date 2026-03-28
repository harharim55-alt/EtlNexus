import { Sparkles, Trash2 } from "lucide-react";

interface TerminalHeaderProps {
  onClear: () => void;
}

export function TerminalHeader({ onClear }: TerminalHeaderProps) {
  return (
    <div className="border-b border-border px-6 py-4 flex items-center justify-between bg-card/50 backdrop-blur shrink-0">
      <div className="flex items-center gap-3">
        <div className="bg-gradient-to-br from-indigo-500 to-purple-600 p-2 rounded-lg">
          <Sparkles className="w-4 h-4 text-white" />
        </div>
        <div>
          <h2 className="text-sm font-semibold text-foreground">AI Architect</h2>
          <p className="text-[10px] font-mono text-text-muted uppercase tracking-widest">
            Data Architecture Intelligence
          </p>
        </div>
      </div>
      <button
        onClick={onClear}
        className="text-text-faint hover:text-text-secondary transition-colors p-2 rounded-lg hover:bg-hover-bg"
        title="Clear history"
      >
        <Trash2 className="w-4 h-4" />
      </button>
    </div>
  );
}
