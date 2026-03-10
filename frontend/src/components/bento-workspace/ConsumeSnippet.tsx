import { Code } from "lucide-react";
import { CopyButton } from "@/components/shared/CopyButton";

interface ConsumeSnippetProps {
  pipelineName: string;
  category?: string;
}

export function ConsumeSnippet({ pipelineName, category }: ConsumeSnippetProps) {
  const importName = pipelineName.toLowerCase().replace(/ /g, "_");
  const isApi = category?.toLowerCase().includes("api") ?? false;

  if (isApi) {
    const apiCode = `from path import api\n\n${importName} = ${importName}(start_date, end_date)`;

    return (
      <div className="bg-[#18181b] border border-white/5 rounded-2xl p-5 shrink-0">
        <div className="flex justify-between items-center mb-4">
          <h3 className="text-[11px] font-mono uppercase tracking-widest text-slate-500 flex items-center gap-2">
            <Code className="w-3.5 h-3.5" /> Import & Consume
          </h3>
          <CopyButton text={apiCode} />
        </div>

        <div className="bg-[#09090b] rounded-xl p-4 border border-white/5 overflow-x-auto">
          <code className="text-xs font-mono leading-relaxed text-slate-300">
            <span className="text-pink-500">from</span> path{" "}
            <span className="text-pink-500">import</span> api
            <br />
            <br />
            <span className="text-indigo-400">{importName}</span> ={" "}
            <span className="text-indigo-400">{importName}</span>(
            <span className="text-emerald-400">start_date</span>,{" "}
            <span className="text-emerald-400">end_date</span>)
          </code>
        </div>
      </div>
    );
  }

  const etlCode = `from etls import ${importName}\n\n${importName}("2026-01-25").consume()`;
  const catalogCode = `from etls import Catalog, Engine\n\nCatalog(Engine.Spark).iceberg.dagger.${importName}("date").consume().as_pyspark()`;

  return (
    <div className="bg-[#18181b] border border-white/5 rounded-2xl p-5 shrink-0">
      <div className="flex justify-between items-center mb-4">
        <h3 className="text-[11px] font-mono uppercase tracking-widest text-slate-500 flex items-center gap-2">
          <Code className="w-3.5 h-3.5" /> Import & Consume
        </h3>
        <CopyButton text={`${etlCode}\n\n${catalogCode}`} />
      </div>

      {/* ETL Import */}
      <div className="bg-[#09090b] rounded-xl p-4 border border-white/5 overflow-x-auto mb-3">
        <code className="text-xs font-mono leading-relaxed text-slate-300">
          <span className="text-pink-500">from</span> etls{" "}
          <span className="text-pink-500">import</span> {importName}
          <br />
          <br />
          <span className="text-indigo-400">{importName}</span>(
          <span className="text-amber-400">"2026-01-25"</span>).consume()
        </code>
      </div>

      {/* Catalog Import */}
      <div className="bg-[#09090b] rounded-xl p-4 border border-white/5 overflow-x-auto">
        <code className="text-xs font-mono leading-relaxed text-slate-300">
          <span className="text-pink-500">from</span> etls{" "}
          <span className="text-pink-500">import</span> Catalog, Engine
          <br />
          <br />
          <span className="text-indigo-400">Catalog</span>(
          <span className="text-emerald-400">Engine</span>.Spark).iceberg.dagger.
          <span className="text-indigo-400">{importName}</span>(
          <span className="text-amber-400">"date"</span>).consume().as_pyspark()
        </code>
      </div>
    </div>
  );
}
