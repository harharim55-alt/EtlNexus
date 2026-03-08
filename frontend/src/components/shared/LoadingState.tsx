export function LoadingState() {
  return (
    <div className="flex flex-col items-center justify-center h-full bg-[#09090b] text-slate-500 gap-4">
      <div className="flex items-center gap-1">
        <div className="w-2 h-8 bg-indigo-500/50 rounded animate-pulse" />
        <div className="w-2 h-12 bg-indigo-500/80 rounded animate-pulse delay-75" />
        <div className="w-2 h-6 bg-indigo-500/30 rounded animate-pulse delay-150" />
      </div>
      <p className="font-mono text-xs tracking-widest uppercase">
        Initializing Registry...
      </p>
    </div>
  );
}
