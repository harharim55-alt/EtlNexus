import { useState } from "react";
import { ChevronRight, Copy, Check } from "lucide-react";
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
      className="absolute bottom-3 right-3 flex items-center gap-1 text-[10px] font-mono text-text-faint hover:text-indigo-400 bg-hover-bg hover:bg-indigo-500/10 px-2 py-1 rounded-md border border-border hover:border-indigo-500/20 transition-all opacity-0 group-hover/code:opacity-100"
    >
      {copied ? <Check className="size-3" /> : <Copy className="size-3" />}
      {copied ? "Copied!" : "Copy"}
    </button>
  );
}

/* ── Styled markdown components ───────────────────────────────────── */

export const markdownComponents: Components = {
  h1: ({ children }) => (
    <h1 className="text-2xl font-bold text-foreground mt-8 mb-5 pb-3 border-b border-border tracking-tight">
      {children}
    </h1>
  ),
  h2: ({ children }) => (
    <h2 className="text-xl font-bold text-foreground mt-9 mb-4 tracking-tight">
      {children}
    </h2>
  ),
  h3: ({ children }) => (
    <h3 className="text-lg font-semibold text-foreground mt-7 mb-3 tracking-tight">
      {children}
    </h3>
  ),
  h4: ({ children }) => (
    <h4 className="text-base font-semibold text-foreground mt-6 mb-2 tracking-tight">
      {children}
    </h4>
  ),
  h5: ({ children }) => (
    <h5 className="text-sm font-semibold text-text-primary mt-5 mb-2 tracking-tight">
      {children}
    </h5>
  ),
  h6: ({ children }) => (
    <h6 className="text-xs font-semibold text-text-primary mt-5 mb-2 uppercase tracking-wider">
      {children}
    </h6>
  ),
  p: ({ children }) => (
    <p className="mb-4 text-text-primary leading-relaxed">{children}</p>
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
    <strong className="text-foreground font-semibold">{children}</strong>
  ),
  em: ({ children }) => <em className="text-text-secondary">{children}</em>,
  blockquote: ({ children }) => (
    <blockquote className="border-l-2 border-indigo-500/40 pl-4 py-0.5 my-3 text-text-secondary italic">
      {children}
    </blockquote>
  ),
  hr: () => (
    <hr className="border-0 h-px bg-gradient-to-r from-transparent via-border-prominent to-transparent my-8" />
  ),
  ul: ({ children }) => <ul className="my-3 space-y-1">{children}</ul>,
  ol: ({ children }) => <ol className="my-3 space-y-1">{children}</ol>,
  li: ({ children }) => (
    <li className="ml-5 list-disc mb-1.5 text-text-primary leading-relaxed marker:text-indigo-500/40">
      {children}
    </li>
  ),
  table: ({ children }) => (
    <div className="my-5 overflow-x-auto custom-scrollbar rounded-xl border border-border">
      <table className="w-full text-sm">{children}</table>
    </div>
  ),
  thead: ({ children }) => (
    <thead className="bg-hover-bg border-b border-border">
      {children}
    </thead>
  ),
  th: ({ children }) => (
    <th className="px-4 py-2.5 text-left text-xs font-semibold text-text-secondary uppercase tracking-wider">
      {children}
    </th>
  ),
  td: ({ children }) => (
    <td className="px-4 py-2.5 text-text-primary border-t border-border">
      {children}
    </td>
  ),
  pre: ({ children }) => (
    <div className="relative group/code my-5">
      <pre className="bg-surface-code border border-border rounded-xl p-5 overflow-x-auto custom-scrollbar">
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
            <span className="absolute top-3 right-4 text-[10px] font-mono text-text-faint uppercase tracking-wider select-none">
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
    <del className="text-text-muted line-through">{children}</del>
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
    <details className="my-4 bg-hover-bg border border-border rounded-xl overflow-hidden group/details">
      {children}
    </details>
  ),
  summary: ({ children }) => (
    <summary className="px-5 py-3 cursor-pointer text-sm font-medium text-text-primary hover:text-foreground hover:bg-hover-bg transition-colors select-none flex items-center gap-2 [&::marker]:hidden [&::-webkit-details-marker]:hidden list-none">
      <ChevronRight className="size-3.5 text-text-muted transition-transform duration-200 group-open/details:rotate-90 shrink-0" />
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
          className="text-right my-4 p-4 bg-hover-bg border border-border rounded-xl"
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
