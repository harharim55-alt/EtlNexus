import {
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
  Languages,
  PanelTopClose,
  HelpCircle,
} from "lucide-react";

/* ── Toolbar helper ───────────────────────────────────────────────── */

export function insertAtCursor(
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

export function insertBlock(
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
      className="p-1.5 text-text-muted hover:text-indigo-400 hover:bg-indigo-500/10 rounded-md transition-all duration-150 border border-transparent hover:border-indigo-500/20"
    >
      <Icon className="size-3.5" />
    </button>
  );
}

function ToolbarSep() {
  return <div className="w-px h-4 bg-hover-bg-strong mx-0.5" />;
}

/* ── Formatting toolbar ───────────────────────────────────────────── */

export function MarkdownToolbar({
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
    <div className="flex items-center gap-0.5 px-4 py-1.5 bg-surface-inset border-b border-border shrink-0 flex-wrap">
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
            : "text-text-muted hover:text-indigo-400 hover:bg-indigo-500/10 border-transparent hover:border-indigo-500/20"
        }`}
      >
        <HelpCircle className="size-3.5" />
      </button>
    </div>
  );
}
