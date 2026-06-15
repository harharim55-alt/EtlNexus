import { Code } from "lucide-react";
import { CopyButton } from "@/components/shared/CopyButton";

interface ConsumeSnippetProps {
  /** The snippet to display (read-only). */
  snippet: string;
}

export function ConsumeSnippet({ snippet }: ConsumeSnippetProps) {
  return (
    <div className="bg-card border border-border rounded-2xl p-5 shrink-0">
      <div className="flex justify-between items-center mb-4">
        <h3 className="text-[11px] font-mono uppercase tracking-widest text-text-muted flex items-center gap-2">
          <Code className="w-3.5 h-3.5" /> Import & Consume
        </h3>
        <CopyButton text={snippet} />
      </div>
      <div className="bg-background rounded-xl p-4 border border-border overflow-x-auto">
        <pre className="text-xs font-mono leading-relaxed text-text-primary whitespace-pre-wrap">{snippet}</pre>
      </div>
    </div>
  );
}
