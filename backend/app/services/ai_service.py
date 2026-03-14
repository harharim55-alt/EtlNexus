"""AI service — chat with catalog context and join insights."""

import uuid

from app.integrations.llm_client import llm_client
from app.repositories.pipeline_repo import PipelineRepository

SYSTEM_PROMPT = """You are an expert data architect assistant for ETL Explorer Hub.
You have access to the organization's data catalog. Help users understand data pipelines,
suggest optimizations, explain lineage, and provide data architecture guidance.

Available pipelines in the catalog:
{catalog_context}

Always be specific and reference actual pipeline names and fields when applicable.
Keep responses concise and actionable."""


class AIService:
    def __init__(self, pipeline_repo: PipelineRepository):
        self.pipeline_repo = pipeline_repo

    async def chat(self, message: str, history: list[dict]) -> str:
        """Process a chat message with catalog context."""
        catalog_context = await self._build_catalog_context()
        system_prompt = SYSTEM_PROMPT.format(catalog_context=catalog_context)

        messages = [
            *[{"role": m["role"], "content": m["content"]} for m in history],
            {"role": "user", "content": message},
        ]

        return await llm_client.chat(messages, system_prompt=system_prompt)

    async def get_join_insight(self, pipeline_id: uuid.UUID) -> str:
        """Get AI-powered insight about potential joins for a pipeline."""
        if not llm_client.is_configured:
            return "AI-powered join insights will be available once the LLM endpoint is configured."

        pipeline = await self.pipeline_repo.get_by_id(pipeline_id)
        if not pipeline:
            return "Pipeline not found."

        field_names = [f.name for f in pipeline.fields]
        all_pipelines = await self.pipeline_repo.get_all_with_fields()

        # Build context about overlapping fields
        overlaps = []
        for other in all_pipelines:
            if other.id == pipeline_id:
                continue
            other_fields = {f.name for f in other.fields}
            shared = set(field_names) & other_fields
            if shared:
                overlaps.append(f"- {other.name}: shared fields [{', '.join(sorted(shared))}]")

        if not overlaps:
            return f"No field overlaps found for {pipeline.name}. Consider adding standardized field names."

        prompt = (
            f"Pipeline '{pipeline.name}' has fields: {', '.join(field_names)}.\n\n"
            f"Field overlaps with other pipelines:\n" + "\n".join(overlaps) + "\n\n"
            "Provide a brief insight (2-3 sentences) about the most valuable joins "
            "and how they could be used for analytics."
        )

        return await llm_client.chat(
            [{"role": "user", "content": prompt}],
            system_prompt="You are a data architect. Be concise and specific.",
        )

    async def _build_catalog_context(self) -> str:
        """Build a summary of the catalog for the system prompt."""
        pipelines = await self.pipeline_repo.get_all()
        if not pipelines:
            return "No pipelines currently in the catalog."

        lines = []
        for p in pipelines[:20]:  # Limit context size
            line = f"- {p.name}"
            if p.category:
                line += f" [{p.category}]"
            if p.description:
                line += f": {p.description[:100]}"
            lines.append(line)

        return "\n".join(lines)
