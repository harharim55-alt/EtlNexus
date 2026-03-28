export function TypingIndicator() {
  return (
    <div className="flex gap-3 items-start">
      <div className="w-7 h-7 rounded-lg bg-indigo-500/10 border border-indigo-500/20 flex items-center justify-center shrink-0">
        <div className="flex gap-1">
          <div className="w-1.5 h-1.5 rounded-full bg-indigo-400 animate-bounce [animation-delay:0ms]" />
          <div className="w-1.5 h-1.5 rounded-full bg-indigo-400 animate-bounce [animation-delay:150ms]" />
          <div className="w-1.5 h-1.5 rounded-full bg-indigo-400 animate-bounce [animation-delay:300ms]" />
        </div>
      </div>
      <div className="bg-hover-bg border border-border rounded-xl px-4 py-2.5 text-sm text-text-muted font-mono">
        Processing query...
      </div>
    </div>
  );
}
