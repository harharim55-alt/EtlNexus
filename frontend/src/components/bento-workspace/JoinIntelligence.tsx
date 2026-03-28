import { Database, Sparkles } from "lucide-react";
import { useQuery } from "@tanstack/react-query";
import { useJoinSuggestions } from "@/hooks/use-join-suggestions";
import { fetchJoinInsight } from "@/api/ai";
import { Skeleton } from "@/components/ui/skeleton";
import { stripDummy } from "@/lib/format";

interface JoinIntelligenceProps {
  pipelineId: string;
}

export function JoinIntelligence({ pipelineId }: JoinIntelligenceProps) {
  const { data, isLoading } = useJoinSuggestions(pipelineId);
  const { data: aiInsight, isLoading: aiLoading } = useQuery({
    queryKey: ["join-insight", pipelineId],
    queryFn: () => fetchJoinInsight(pipelineId),
    enabled: !!pipelineId,
    staleTime: 10 * 60_000,
  });

  return (
    <div className="bg-card border border-border rounded-2xl p-5 flex-1 flex flex-col gap-5">
      {/* Schema Matches */}
      <div>
        <div className="flex items-center gap-2 mb-3">
          <h3 className="text-[11px] font-mono uppercase tracking-widest text-text-secondary flex items-center gap-2">
            <Database className="w-3.5 h-3.5" /> Schema Matches
          </h3>
        </div>
        {isLoading ? (
          <div className="space-y-2">
            <Skeleton className="h-16 bg-hover-bg rounded-lg" />
            <Skeleton className="h-16 bg-hover-bg rounded-lg" />
          </div>
        ) : data && data.schema_matches.length > 0 ? (
          <div className="space-y-2">
            {data.schema_matches.slice(0, 2).map((match) => (
              <div
                key={match.pipeline_id}
                className="p-2.5 rounded-lg bg-hover-bg border border-border flex flex-col gap-1.5"
              >
                <div className="font-medium text-[13px] text-text-primary">
                  {stripDummy(match.pipeline_name)}
                </div>
                <div className="flex flex-wrap gap-1.5 items-center">
                  <span className="text-[10px] text-text-muted font-mono">
                    ON:
                  </span>
                  {match.shared_fields.map((f) => (
                    <span
                      key={f}
                      className="text-[10px] bg-background text-text-primary px-1.5 py-0.5 rounded font-mono border border-border-prominent"
                    >
                      {f}
                    </span>
                  ))}
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div className="text-xs text-text-faint font-mono">
            No schema matches found
          </div>
        )}
      </div>

      {/* AI Insight placeholder */}
      <div>
        <div className="flex items-center gap-2 mb-3">
          <h3 className="text-[11px] font-mono uppercase tracking-widest text-indigo-300 flex items-center gap-2">
            <Sparkles className="w-3.5 h-3.5" /> AI Insight
          </h3>
        </div>
        {aiLoading ? (
          <Skeleton className="h-16 bg-indigo-500/5 rounded-lg" />
        ) : (
          <div className="p-3.5 rounded-lg bg-indigo-500/5 border border-indigo-500/10 text-xs text-indigo-200/80 leading-relaxed">
            {aiInsight?.insight ??
              "AI-powered join insights will be available once the LLM endpoint is configured."}
          </div>
        )}
      </div>
    </div>
  );
}
