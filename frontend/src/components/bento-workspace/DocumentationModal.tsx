import { useState, useEffect, useCallback, useRef, useMemo } from "react";
import {
  FileText,
  Edit3,
  Save,
  X,
  Copy,
  Check,
  Bold,
  Italic,
  Strikethrough,
  Heading1,
  Heading2,
  Heading3,
  Heading4,
  List,
  ListOrdered,
  ListChecks,
  Link,
  Code,
  Table,
  Minus,
  ChevronRight,
  Languages,
  PanelTopClose,
  HelpCircle,
} from "lucide-react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import remarkDirective from "remark-directive";
import remarkDirectiveRehype from "remark-directive-rehype";
import rehypeRaw from "rehype-raw";
import rehypeHighlight from "rehype-highlight";
import type { Components } from "react-markdown";

/* ── Copy button for code blocks ──────────────────────────────────── */

function CopyButton({ code }: { code: string }) {
  const [copied, setCopied] = useState(false);
  return (
    <button
      onClick={async () => {
        await navigator.clipboard.writeText(code);
        setCopied(true);
        setTimeout(() => setCopied(false), 2000);
      }}
      className="absolute bottom-3 right-3 flex items-center gap-1 text-[10px] font-mono text-slate-600 hover:text-indigo-400 bg-white/[0.04] hover:bg-indigo-500/10 px-2 py-1 rounded-md border border-white/[0.06] hover:border-indigo-500/20 transition-all opacity-0 group-hover/code:opacity-100"
    >
      {copied ? <Check className="size-3" /> : <Copy className="size-3" />}
      {copied ? "Copied!" : "Copy"}
    </button>
  );
}

/* ── Styled markdown components ───────────────────────────────────── */

const markdownComponents: Components = {
  h1: ({ children }) => (
    <h1 className="text-2xl font-bold text-white mt-8 mb-5 pb-3 border-b border-white/8 tracking-tight">
      {children}
    </h1>
  ),
  h2: ({ children }) => (
    <h2 className="text-xl font-bold text-white mt-9 mb-4 tracking-tight">
      {children}
    </h2>
  ),
  h3: ({ children }) => (
    <h3 className="text-lg font-semibold text-white mt-7 mb-3 tracking-tight">
      {children}
    </h3>
  ),
  h4: ({ children }) => (
    <h4 className="text-base font-semibold text-white mt-6 mb-2 tracking-tight">
      {children}
    </h4>
  ),
  h5: ({ children }) => (
    <h5 className="text-sm font-semibold text-slate-200 mt-5 mb-2 tracking-tight">
      {children}
    </h5>
  ),
  h6: ({ children }) => (
    <h6 className="text-xs font-semibold text-slate-300 mt-5 mb-2 uppercase tracking-wider">
      {children}
    </h6>
  ),
  p: ({ children }) => (
    <p className="mb-4 text-slate-300 leading-relaxed">{children}</p>
  ),
  a: ({ href, children }) => (
    <a
      href={href}
      className="text-indigo-400 hover:text-indigo-300 underline underline-offset-2 decoration-indigo-500/30 hover:decoration-indigo-400/60 transition-colors"
      target="_blank"
      rel="noopener noreferrer"
    >
      {children}
    </a>
  ),
  strong: ({ children }) => (
    <strong className="text-white font-semibold">{children}</strong>
  ),
  em: ({ children }) => <em className="text-slate-400">{children}</em>,
  blockquote: ({ children }) => (
    <blockquote className="border-l-2 border-indigo-500/40 pl-4 py-0.5 my-3 text-slate-400 italic">
      {children}
    </blockquote>
  ),
  hr: () => (
    <hr className="border-0 h-px bg-gradient-to-r from-transparent via-white/10 to-transparent my-8" />
  ),
  ul: ({ children }) => <ul className="my-3 space-y-1">{children}</ul>,
  ol: ({ children }) => <ol className="my-3 space-y-1">{children}</ol>,
  li: ({ children }) => (
    <li className="ml-5 list-disc mb-1.5 text-slate-300 leading-relaxed marker:text-indigo-500/40">
      {children}
    </li>
  ),
  table: ({ children }) => (
    <div className="my-5 overflow-x-auto custom-scrollbar rounded-xl border border-white/[0.06]">
      <table className="w-full text-sm">{children}</table>
    </div>
  ),
  thead: ({ children }) => (
    <thead className="bg-white/[0.03] border-b border-white/[0.06]">
      {children}
    </thead>
  ),
  th: ({ children }) => (
    <th className="px-4 py-2.5 text-left text-xs font-semibold text-slate-400 uppercase tracking-wider">
      {children}
    </th>
  ),
  td: ({ children }) => (
    <td className="px-4 py-2.5 text-slate-300 border-t border-white/[0.04]">
      {children}
    </td>
  ),
  pre: ({ children }) => (
    <div className="relative group/code my-5">
      <pre className="bg-[#08080d] border border-white/5 rounded-xl p-5 overflow-x-auto custom-scrollbar">
        {children}
      </pre>
    </div>
  ),
  code: ({ className, children }) => {
    const isBlock = className?.includes("language-") || className?.includes("hljs");
    if (isBlock) {
      const lang = className?.replace(/language-|hljs /g, "").trim() ?? "";
      const codeText = String(children).replace(/\n$/, "");
      return (
        <>
          {lang && (
            <span className="absolute top-3 right-4 text-[10px] font-mono text-slate-600 uppercase tracking-wider select-none">
              {lang}
            </span>
          )}
          <code
            className={`text-[13px] leading-relaxed font-mono ${className ?? ""}`}
          >
            {children}
          </code>
          <CopyButton code={codeText} />
        </>
      );
    }
    return (
      <code className="bg-indigo-500/10 text-indigo-300 px-1.5 py-0.5 rounded text-[13px] font-mono border border-indigo-500/15">
        {children}
      </code>
    );
  },
  del: ({ children }) => (
    <del className="text-slate-500 line-through">{children}</del>
  ),
  input: ({ checked, ...rest }) => (
    <input
      {...rest}
      checked={checked}
      disabled
      className="mr-2 accent-indigo-500"
    />
  ),
  // Collapsible sections
  details: ({ children }) => (
    <details className="my-4 bg-white/[0.02] border border-white/[0.06] rounded-xl overflow-hidden group/details">
      {children}
    </details>
  ),
  summary: ({ children }) => (
    <summary className="px-5 py-3 cursor-pointer text-sm font-medium text-slate-300 hover:text-white hover:bg-white/[0.03] transition-colors select-none flex items-center gap-2 [&::marker]:hidden [&::-webkit-details-marker]:hidden list-none">
      <ChevronRight className="size-3.5 text-slate-500 transition-transform duration-200 group-open/details:rotate-90 shrink-0" />
      {children}
    </summary>
  ),
  // RTL support via dir attribute
  div: ({ dir, lang, children, className, ...rest }: any) => {
    if (dir === "rtl") {
      return (
        <div
          dir="rtl"
          lang={lang || "he"}
          className="text-right my-4 p-4 bg-white/[0.02] border border-white/[0.06] rounded-xl"
          style={{ direction: "rtl", unicodeBidi: "embed" }}
        >
          {children}
        </div>
      );
    }
    return (
      <div className={className} {...rest}>
        {children}
      </div>
    );
  },
  // Footnote section
  section: ({ children, className, ...rest }: any) => (
    <section className={className} {...rest}>
      {children}
    </section>
  ),
};

/* ── Toolbar helper ───────────────────────────────────────────────── */

function insertAtCursor(
  textareaRef: React.RefObject<HTMLTextAreaElement | null>,
  editValue: string,
  setEditValue: (v: string) => void,
  before: string,
  after: string = "",
  opts?: { newline?: boolean; placeholder?: string },
) {
  const el = textareaRef.current;
  if (!el) return;
  const start = el.selectionStart;
  const end = el.selectionEnd;
  const selected = editValue.slice(start, end);
  const text = selected || opts?.placeholder || "";
  const prefix = opts?.newline && start > 0 && editValue[start - 1] !== "\n" ? "\n" : "";
  const insertion = `${prefix}${before}${text}${after}`;
  const newValue = editValue.slice(0, start) + insertion + editValue.slice(end);
  setEditValue(newValue);
  // Restore cursor after React re-render
  const cursorPos = start + prefix.length + before.length + text.length;
  requestAnimationFrame(() => {
    el.focus();
    el.selectionStart = start + prefix.length + before.length;
    el.selectionEnd = cursorPos;
  });
}

function insertBlock(
  textareaRef: React.RefObject<HTMLTextAreaElement | null>,
  editValue: string,
  setEditValue: (v: string) => void,
  block: string,
) {
  const el = textareaRef.current;
  if (!el) return;
  const start = el.selectionStart;
  const prefix = start > 0 && editValue[start - 1] !== "\n" ? "\n\n" : start > 0 ? "\n" : "";
  const newValue = editValue.slice(0, start) + prefix + block + editValue.slice(start);
  setEditValue(newValue);
  requestAnimationFrame(() => {
    el.focus();
    el.selectionStart = el.selectionEnd = start + prefix.length + block.length;
  });
}

/* ── Toolbar button ───────────────────────────────────────────────── */

function ToolbarBtn({
  icon: Icon,
  label,
  onClick,
}: {
  icon: typeof Bold;
  label: string;
  onClick: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      title={label}
      className="p-1.5 text-slate-500 hover:text-indigo-400 hover:bg-indigo-500/10 rounded-md transition-all duration-150 border border-transparent hover:border-indigo-500/20"
    >
      <Icon className="size-3.5" />
    </button>
  );
}

function ToolbarSep() {
  return <div className="w-px h-4 bg-white/[0.06] mx-0.5" />;
}

/* ── Formatting toolbar ───────────────────────────────────────────── */

function MarkdownToolbar({
  textareaRef,
  editValue,
  setEditValue,
  onToggleCheatsheet,
  cheatsheetOpen,
}: {
  textareaRef: React.RefObject<HTMLTextAreaElement | null>;
  editValue: string;
  setEditValue: (v: string) => void;
  onToggleCheatsheet: () => void;
  cheatsheetOpen: boolean;
}) {
  const ins = (before: string, after = "", opts?: { newline?: boolean; placeholder?: string }) =>
    insertAtCursor(textareaRef, editValue, setEditValue, before, after, opts);
  const block = (b: string) => insertBlock(textareaRef, editValue, setEditValue, b);

  return (
    <div className="flex items-center gap-0.5 px-4 py-1.5 bg-[#0c0c10] border-b border-white/[0.04] shrink-0 flex-wrap">
      {/* Text formatting */}
      <ToolbarBtn icon={Bold} label="Bold (Ctrl+B)" onClick={() => ins("**", "**", { placeholder: "bold" })} />
      <ToolbarBtn icon={Italic} label="Italic" onClick={() => ins("*", "*", { placeholder: "italic" })} />
      <ToolbarBtn icon={Strikethrough} label="Strikethrough" onClick={() => ins("~~", "~~", { placeholder: "text" })} />

      <ToolbarSep />

      {/* Headings */}
      <ToolbarBtn icon={Heading1} label="Heading 1" onClick={() => ins("# ", "", { newline: true, placeholder: "Heading" })} />
      <ToolbarBtn icon={Heading2} label="Heading 2" onClick={() => ins("## ", "", { newline: true, placeholder: "Heading" })} />
      <ToolbarBtn icon={Heading3} label="Heading 3" onClick={() => ins("### ", "", { newline: true, placeholder: "Heading" })} />
      <ToolbarBtn icon={Heading4} label="Heading 4" onClick={() => ins("#### ", "", { newline: true, placeholder: "Heading" })} />

      <ToolbarSep />

      {/* Lists */}
      <ToolbarBtn icon={List} label="Bullet list" onClick={() => ins("- ", "", { newline: true, placeholder: "Item" })} />
      <ToolbarBtn icon={ListOrdered} label="Numbered list" onClick={() => ins("1. ", "", { newline: true, placeholder: "Item" })} />
      <ToolbarBtn
        icon={ListChecks}
        label="Task list"
        onClick={() => block("- [ ] Task 1\n- [ ] Task 2\n- [ ] Task 3")}
      />

      <ToolbarSep />

      {/* Insert */}
      <ToolbarBtn icon={Link} label="Link" onClick={() => ins("[", "](url)", { placeholder: "text" })} />
      <ToolbarBtn
        icon={Code}
        label="Code block"
        onClick={() => block("```python\n# code here\n```")}
      />
      <ToolbarBtn
        icon={Table}
        label="Table"
        onClick={() => block("| Column 1 | Column 2 | Column 3 |\n|----------|----------|----------|\n| Cell 1   | Cell 2   | Cell 3   |\n| Cell 4   | Cell 5   | Cell 6   |")}
      />
      <ToolbarBtn icon={Minus} label="Horizontal rule" onClick={() => block("---")} />

      <ToolbarSep />

      {/* Special */}
      <ToolbarBtn
        icon={PanelTopClose}
        label="Collapsible section"
        onClick={() =>
          block(
            "<details>\n<summary>Click to expand</summary>\n\nContent here\n\n</details>",
          )
        }
      />
      <ToolbarBtn
        icon={Languages}
        label="RTL / Hebrew block"
        onClick={() =>
          block(
            '<div dir="rtl" lang="he">\n\n\u05D8\u05E7\u05E1\u05D8 \u05D1\u05E2\u05D1\u05E8\u05D9\u05EA\n\n</div>',
          )
        }
      />

      <div className="flex-1" />

      {/* Help */}
      <button
        type="button"
        onClick={onToggleCheatsheet}
        title="Markdown cheatsheet"
        className={`p-1.5 rounded-md transition-all duration-150 border ${
          cheatsheetOpen
            ? "text-indigo-400 bg-indigo-500/10 border-indigo-500/20"
            : "text-slate-500 hover:text-indigo-400 hover:bg-indigo-500/10 border-transparent hover:border-indigo-500/20"
        }`}
      >
        <HelpCircle className="size-3.5" />
      </button>
    </div>
  );
}

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

function CheatsheetPanel({ onClose }: { onClose: () => void }) {
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
      className="absolute top-full right-0 mt-2 z-50 w-[380px] bg-[#111116] border border-white/[0.08] rounded-xl shadow-2xl shadow-black/50 animate-in fade-in zoom-in-95 duration-150 overflow-hidden"
    >
      <div className="px-4 py-3 border-b border-white/[0.06] flex items-center justify-between">
        <span className="text-xs font-semibold text-white tracking-tight">Markdown Cheatsheet</span>
        <button onClick={onClose} className="p-1 text-slate-500 hover:text-white transition-colors rounded">
          <X className="size-3" />
        </button>
      </div>
      <div className="max-h-[320px] overflow-y-auto custom-scrollbar">
        <table className="w-full text-[11px]">
          <thead>
            <tr className="border-b border-white/[0.04]">
              <th className="text-left px-4 py-2 text-slate-500 font-medium uppercase tracking-wider">Syntax</th>
              <th className="text-left px-4 py-2 text-slate-500 font-medium uppercase tracking-wider">Result</th>
            </tr>
          </thead>
          <tbody>
            {cheatsheetRows.map(([syntax, desc], i) => (
              <tr key={i} className="border-b border-white/[0.02] hover:bg-white/[0.02] transition-colors">
                <td className="px-4 py-1.5">
                  <code className="font-mono text-indigo-300/80 bg-indigo-500/[0.06] px-1.5 py-0.5 rounded text-[10px]">
                    {syntax}
                  </code>
                </td>
                <td className="px-4 py-1.5 text-slate-400">{desc}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

/* ── Empty state ──────────────────────────────────────────────────── */

function EmptyDocState({ canEdit }: { canEdit: boolean }) {
  return (
    <div className="flex flex-col items-center justify-center py-20 gap-4">
      <div className="size-12 rounded-xl bg-white/[0.03] border border-white/[0.06] flex items-center justify-center">
        <FileText className="size-5 text-slate-600" />
      </div>
      <div className="text-center">
        <p className="text-sm text-slate-500 font-medium">
          No documentation yet
        </p>
        <p className="text-[11px] text-slate-600 mt-1">
          {canEdit
            ? "Switch to Edit to start writing in Markdown"
            : "Only team members can add documentation"}
        </p>
      </div>
    </div>
  );
}

/* ── Component ─────────────────────────────────────────────────────── */

interface DocumentationModalProps {
  open: boolean;
  onClose: () => void;
  pipelineName: string;
  documentation: string | null;
  onSave: (documentation: string) => void;
  isSaving: boolean;
  canEdit: boolean;
}

export function DocumentationModal({
  open,
  onClose,
  pipelineName,
  documentation,
  onSave,
  isSaving,
  canEdit,
}: DocumentationModalProps) {
  const [isEditing, setIsEditing] = useState(false);
  const [editValue, setEditValue] = useState(documentation ?? "");
  const [cheatsheetOpen, setCheatsheetOpen] = useState(false);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const gutterRef = useRef<HTMLDivElement>(null);

  const lines = useMemo(() => editValue.split("\n"), [editValue]);
  const previewContent = editValue || documentation || "";

  useEffect(() => {
    setEditValue(documentation ?? "");
  }, [documentation]);

  useEffect(() => {
    if (open) {
      setIsEditing(false);
      setEditValue(documentation ?? "");
      setCheatsheetOpen(false);
    }
  }, [open, documentation]);

  useEffect(() => {
    if (isEditing && textareaRef.current) {
      textareaRef.current.focus();
    }
  }, [isEditing]);

  // Escape to close + Ctrl+S to save
  const handleKeyDown = useCallback(
    (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
      if (e.key === "s" && (e.metaKey || e.ctrlKey) && isEditing) {
        e.preventDefault();
        onSave(editValue);
      }
    },
    [onClose, isEditing, editValue, onSave],
  );

  useEffect(() => {
    if (!open) return;
    document.addEventListener("keydown", handleKeyDown);
    document.body.style.overflow = "hidden";
    return () => {
      document.removeEventListener("keydown", handleKeyDown);
      document.body.style.overflow = "";
    };
  }, [open, handleKeyDown]);

  const handleSave = () => {
    onSave(editValue);
    setIsEditing(false);
  };

  const syncGutterScroll = () => {
    if (gutterRef.current && textareaRef.current) {
      gutterRef.current.scrollTop = textareaRef.current.scrollTop;
    }
  };

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 sm:p-6">
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-black/80 backdrop-blur-sm animate-in fade-in duration-200"
        onClick={onClose}
      />

      {/* Modal */}
      <div className="relative w-full max-w-5xl h-[85vh] bg-[#0d0d12] border border-white/[0.08] rounded-2xl shadow-2xl shadow-black/50 flex flex-col overflow-hidden animate-in fade-in zoom-in-95 duration-200">
        {/* ── Header ─────────────────────────────────────────────── */}
        <div className="px-7 py-4 border-b border-white/[0.08] bg-[#111116] flex items-center justify-between shrink-0">
          <div className="flex items-center gap-4">
            <div className="size-9 bg-indigo-500/10 border border-indigo-500/20 rounded-xl flex items-center justify-center">
              <FileText className="size-[18px] text-indigo-400" />
            </div>
            <div>
              <h2 className="text-lg font-semibold text-white tracking-tight">
                {pipelineName}
              </h2>
              <p className="text-[11px] text-slate-500 font-mono mt-0.5">
                Documentation.md
              </p>
            </div>
          </div>

          <div className="flex items-center gap-3">
            {/* Segmented control: Preview / Edit */}
            <div className="flex bg-white/[0.04] rounded-lg p-0.5 border border-white/[0.06]">
              <button
                onClick={() => { setIsEditing(false); setCheatsheetOpen(false); }}
                className={`flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-md transition-all duration-200 ${
                  !isEditing
                    ? "bg-white/[0.08] text-white shadow-sm"
                    : "text-slate-500 hover:text-slate-300"
                }`}
              >
                <FileText className="size-3" />
                Preview
              </button>
              <button
                onClick={() => canEdit && setIsEditing(true)}
                disabled={!canEdit}
                className={`flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-md transition-all duration-200 ${
                  !canEdit
                    ? "text-slate-600 cursor-not-allowed opacity-40"
                    : isEditing
                      ? "bg-white/[0.08] text-white shadow-sm"
                      : "text-slate-500 hover:text-slate-300"
                }`}
                title={!canEdit ? "You don't have permission to edit this pipeline's documentation" : undefined}
              >
                <Edit3 className="size-3" />
                Edit
              </button>
            </div>

            {/* Save (only in edit mode) */}
            {isEditing && canEdit && (
              <button
                onClick={handleSave}
                disabled={isSaving}
                className="flex items-center gap-2 px-4 py-1.5 bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white text-sm font-medium rounded-lg transition-colors shadow-lg shadow-indigo-500/15 animate-in fade-in duration-150"
              >
                <Save className="size-3.5" />
                {isSaving ? "Saving\u2026" : "Save"}
              </button>
            )}

            <div className="w-px h-5 bg-white/[0.08] mx-1" />

            <button
              onClick={onClose}
              className="p-2 text-slate-500 hover:text-white hover:bg-white/5 rounded-lg transition-all duration-200 border border-transparent hover:border-white/[0.08]"
            >
              <X className="size-[18px]" />
            </button>
          </div>
        </div>

        {/* ── Toolbar (edit mode) ────────────────────────────────── */}
        {isEditing && (
          <div className="relative shrink-0">
            <MarkdownToolbar
              textareaRef={textareaRef}
              editValue={editValue}
              setEditValue={setEditValue}
              onToggleCheatsheet={() => setCheatsheetOpen((v) => !v)}
              cheatsheetOpen={cheatsheetOpen}
            />
            {cheatsheetOpen && (
              <CheatsheetPanel onClose={() => setCheatsheetOpen(false)} />
            )}
          </div>
        )}

        {/* ── Body ───────────────────────────────────────────────── */}
        <div className="flex-1 overflow-auto bg-[#09090b] custom-scrollbar">
          {isEditing ? (
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
                onChange={(e) => setEditValue(e.target.value)}
                onScroll={syncGutterScroll}
                className="flex-1 h-full min-h-full bg-transparent text-slate-300 font-mono text-sm resize-none focus:outline-none py-8 px-6 leading-relaxed placeholder:text-slate-600"
                placeholder="# Start writing documentation here..."
                spellCheck={false}
              />
            </div>
          ) : (
            <div className="p-10 max-w-4xl mx-auto">
              {previewContent.trim() ? (
                <ReactMarkdown
                  remarkPlugins={[remarkGfm, remarkDirective, remarkDirectiveRehype]}
                  rehypePlugins={[rehypeRaw, rehypeHighlight]}
                  components={markdownComponents}
                >
                  {previewContent}
                </ReactMarkdown>
              ) : (
                <EmptyDocState canEdit={canEdit} />
              )}
            </div>
          )}
        </div>

        {/* ── Footer ─────────────────────────────────────────────── */}
        <div className="px-7 py-2.5 bg-[#111116] border-t border-white/[0.08] text-[11px] font-mono text-slate-600 flex justify-between shrink-0">
          {isEditing ? (
            <>
              <span>Markdown + GFM &middot; Use toolbar for formatting</span>
              <span>Ctrl+S to save &middot; Esc to close</span>
            </>
          ) : (
            <>
              <span>{canEdit ? "Read-only preview" : "View only — you don\u2019t have edit permissions"}</span>
              <span>Esc to close</span>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
