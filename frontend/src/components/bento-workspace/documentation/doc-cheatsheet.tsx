import { useEffect, useRef } from "react";
import { X } from "lucide-react";

/* ── Cheatsheet overlay ───────────────────────────────────────────── */

const cheatsheetRows = [
  ["**bold**", "Bold text"],
  ["*italic*", "Italic text"],
  ["~~strike~~", "Strikethrough"],
  ["# Heading", "Heading 1\u20136 (# to ######)"],
  ["`code`", "Inline code"],
  ["```lang\\n...\\n```", "Code block with highlighting"],
  ["> quote", "Blockquote"],
  ["- item", "Bullet list"],
  ["1. item", "Numbered list"],
  ["- [ ] task", "Task list checkbox"],
  ["[text](url)", "Hyperlink"],
  ["| A | B |\\n|---|---|", "Table"],
  ["---", "Horizontal rule"],
  ["<details>", "Collapsible section"],
  ['<div dir="rtl">', "Right-to-left text"],
];

export function CheatsheetPanel({ onClose }: { onClose: () => void }) {
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const handleClick = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) onClose();
    };
    const handleKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") { e.stopPropagation(); onClose(); }
    };
    document.addEventListener("mousedown", handleClick);
    document.addEventListener("keydown", handleKey, true);
    return () => {
      document.removeEventListener("mousedown", handleClick);
      document.removeEventListener("keydown", handleKey, true);
    };
  }, [onClose]);

  return (
    <div
      ref={ref}
      className="absolute top-full right-0 mt-2 z-50 w-[380px] bg-surface-raised border border-border rounded-xl shadow-2xl shadow-black/50 animate-in fade-in zoom-in-95 duration-150 overflow-hidden"
    >
      <div className="px-4 py-3 border-b border-border flex items-center justify-between">
        <span className="text-xs font-semibold text-foreground tracking-tight">Markdown Cheatsheet</span>
        <button onClick={onClose} className="p-1 text-text-muted hover:text-foreground transition-colors rounded">
          <X className="size-3" />
        </button>
      </div>
      <div className="max-h-[320px] overflow-y-auto custom-scrollbar">
        <table className="w-full text-[11px]">
          <thead>
            <tr className="border-b border-border">
              <th className="text-left px-4 py-2 text-text-muted font-medium uppercase tracking-wider">Syntax</th>
              <th className="text-left px-4 py-2 text-text-muted font-medium uppercase tracking-wider">Result</th>
            </tr>
          </thead>
          <tbody>
            {cheatsheetRows.map(([syntax, desc], i) => (
              <tr key={i} className="border-b border-border hover:bg-hover-bg transition-colors">
                <td className="px-4 py-1.5">
                  <code className="font-mono text-indigo-300/80 bg-indigo-500/[0.06] px-1.5 py-0.5 rounded text-[10px]">
                    {syntax}
                  </code>
                </td>
                <td className="px-4 py-1.5 text-text-secondary">{desc}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
