import { Sparkles } from "lucide-react";
import { useQuery } from "@tanstack/react-query";
import { fetchJoinInsight } from "@/api/ai";
import { Skeleton } from "@/components/ui/skeleton";

interface JoinIntelligenceProps {
  pipelineId: string;
}

export function JoinIntelligence({ pipelineId }: JoinIntelligenceProps) {
  const { data: aiInsight, isLoading: aiLoading } = useQuery({
    queryKey: ["join-insight", pipelineId],
    queryFn: () => fetchJoinInsight(pipelineId),
    enabled: !!pipelineId,
    staleTime: 10 * 60_000,
  });

  return (
    <div className="bg-card border border-border rounded-2xl p-5 flex-1 flex flex-col gap-5">
      {/* AI Insight */}
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
