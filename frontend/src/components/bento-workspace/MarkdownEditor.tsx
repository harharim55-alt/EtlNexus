import { useRef, useMemo } from "react";
import { MarkdownToolbar } from "./documentation/doc-toolbar";
import { CheatsheetPanel } from "./documentation/doc-cheatsheet";

/* ── Props ─────────────────────────────────────────────────────────── */

interface MarkdownEditorProps {
  editValue: string;
  onEditValueChange: (value: string) => void;
  textareaRef: React.RefObject<HTMLTextAreaElement | null>;
  cheatsheetOpen: boolean;
  onToggleCheatsheet: () => void;
  onCloseCheatsheet: () => void;
}

/* ── Component ─────────────────────────────────────────────────────── */

export function MarkdownEditor({
  editValue,
  onEditValueChange,
  textareaRef,
  cheatsheetOpen,
  onToggleCheatsheet,
  onCloseCheatsheet,
}: MarkdownEditorProps) {
  const gutterRef = useRef<HTMLDivElement>(null);
  const lines = useMemo(() => editValue.split("\n"), [editValue]);

  const syncGutterScroll = () => {
    if (gutterRef.current && textareaRef.current) {
      gutterRef.current.scrollTop = textareaRef.current.scrollTop;
    }
  };

  return (
    <>
      {/* Toolbar */}
      <div className="relative shrink-0">
        <MarkdownToolbar
          textareaRef={textareaRef}
          editValue={editValue}
          setEditValue={onEditValueChange}
          onToggleCheatsheet={onToggleCheatsheet}
          cheatsheetOpen={cheatsheetOpen}
        />
        {cheatsheetOpen && (
          <CheatsheetPanel onClose={onCloseCheatsheet} />
        )}
      </div>

      {/* Editor body */}
      <div className="flex-1 overflow-auto bg-[#09090b] custom-scrollbar">
        <div className="flex h-full">
          {/* Line number gutter */}
          <div
            ref={gutterRef}
            className="shrink-0 py-8 pl-5 pr-3 text-right select-none overflow-hidden border-r border-white/[0.04]"
          >
            {lines.map((_, i) => (
              <div
                key={i}
                className="text-[11px] font-mono text-slate-700 leading-relaxed"
                style={{ height: "1.625rem" }}
              >
                {i + 1}
              </div>
            ))}
          </div>
          {/* Textarea */}
          <textarea
            ref={textareaRef}
            value={editValue}
            onChange={(e) => onEditValueChange(e.target.value)}
            onScroll={syncGutterScroll}
            className="flex-1 h-full min-h-full bg-transparent text-slate-300 font-mono text-sm resize-none focus:outline-none py-8 px-6 leading-relaxed placeholder:text-slate-600"
            placeholder="# Start writing documentation here..."
            spellCheck={false}
          />
        </div>
      </div>
    </>
  );
}
