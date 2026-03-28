import { useMemo } from "react";
import type { AdminTeam, VisibilityGrant } from "@/types/admin";
import type { PipelineListItem } from "@/types/pipeline";

interface VisibilityMatrixProps {
  grants: VisibilityGrant[];
  teams: AdminTeam[];
  pipelines: PipelineListItem[];
}

type CellValue = {
  level: "viewer" | "editor";
  grantId: string;
} | null;

/**
 * Cross-tabulation matrix: grantee teams (rows) vs source teams/pipelines (columns).
 * Each cell shows the grant level (viewer/editor) with color coding.
 */
export function VisibilityMatrix({ grants, teams, pipelines }: VisibilityMatrixProps) {
  const pipelineMap = useMemo(
    () => new Map(pipelines.map((p) => [p.id, p.name])),
    [pipelines],
  );

  // Only include team-level grants in the matrix (user grants are excluded)
  const teamGrants = useMemo(
    () => grants.filter((g) => g.grantee_team_id),
    [grants],
  );

  // Collect unique grantee team IDs (rows)
  const granteeTeams = useMemo(() => {
    const ids = new Set(teamGrants.map((g) => g.grantee_team_id!));
    return teams.filter((t) => ids.has(t.id));
  }, [teamGrants, teams]);

  // Collect unique target columns: source teams first, then individual pipelines
  const columns = useMemo(() => {
    const cols: { key: string; label: string; type: "team" | "pipeline" }[] = [];
    const seenKeys = new Set<string>();

    for (const g of teamGrants) {
      if (g.source_team_id) {
        const key = `team:${g.source_team_id}`;
        if (!seenKeys.has(key)) {
          seenKeys.add(key);
          const team = teams.find((t) => t.id === g.source_team_id);
          cols.push({
            key,
            label: g.source_team_name ?? team?.name ?? "Unknown",
            type: "team",
          });
        }
      } else if (g.pipeline_id) {
        const key = `pipeline:${g.pipeline_id}`;
        if (!seenKeys.has(key)) {
          seenKeys.add(key);
          cols.push({
            key,
            label: pipelineMap.get(g.pipeline_id) ?? g.pipeline_id,
            type: "pipeline",
          });
        }
      }
    }

    // Sort: teams first, then pipelines, each alphabetically
    cols.sort((a, b) => {
      if (a.type !== b.type) return a.type === "team" ? -1 : 1;
      return a.label.localeCompare(b.label);
    });

    return cols;
  }, [teamGrants, teams, pipelineMap]);

  // Build the matrix lookup: [granteeTeamId][columnKey] -> CellValue
  const matrix = useMemo(() => {
    const m = new Map<string, Map<string, CellValue>>();

    for (const g of teamGrants) {
      const rowId = g.grantee_team_id!;
      if (!m.has(rowId)) m.set(rowId, new Map());
      const row = m.get(rowId)!;

      let colKey: string | null = null;
      if (g.source_team_id) colKey = `team:${g.source_team_id}`;
      else if (g.pipeline_id) colKey = `pipeline:${g.pipeline_id}`;

      if (colKey) {
        const existing = row.get(colKey);
        // If there is already a grant, prefer editor over viewer
        if (!existing || g.grant_level === "editor") {
          row.set(colKey, {
            level: g.grant_level as "viewer" | "editor",
            grantId: g.id,
          });
        }
      }
    }
    return m;
  }, [teamGrants]);

  if (granteeTeams.length === 0 || columns.length === 0) {
    return (
      <div className="text-center py-12 text-text-faint text-xs font-mono">
        No team-level grants to display in matrix view.
        <br />
        <span className="text-text-faint">
          User-level grants are only visible in list view.
        </span>
      </div>
    );
  }

  return (
    <div className="space-y-3">
      <div className="overflow-x-auto custom-scrollbar rounded-xl border border-border">
        <table className="w-full border-collapse">
          <thead>
            <tr>
              {/* Top-left corner cell */}
              <th className="sticky left-0 z-20 bg-card border-b border-r border-border px-4 py-3 text-left text-[10px] font-mono uppercase tracking-wider text-text-muted">
                Grantee
              </th>
              {columns.map((col) => (
                <th
                  key={col.key}
                  className="border-b border-border px-3 py-3 text-center text-[10px] font-mono uppercase tracking-wider text-text-muted whitespace-nowrap"
                >
                  <div className="flex flex-col items-center gap-1">
                    <span
                      className={`text-[8px] px-1.5 py-0.5 rounded border ${
                        col.type === "team"
                          ? "text-teal-400 bg-teal-500/10 border-teal-500/20"
                          : "text-indigo-400 bg-indigo-500/10 border-indigo-500/20"
                      }`}
                    >
                      {col.type}
                    </span>
                    <span className="text-text-secondary">{col.label}</span>
                  </div>
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {granteeTeams.map((team, rowIdx) => {
              const row = matrix.get(team.id);
              return (
                <tr
                  key={team.id}
                  className={
                    rowIdx % 2 === 0 ? "bg-card" : "bg-hover-bg"
                  }
                >
                  <td className="sticky left-0 z-10 bg-inherit border-r border-border px-4 py-2.5 text-sm font-medium text-foreground whitespace-nowrap">
                    {team.name}
                  </td>
                  {columns.map((col) => {
                    const cell = row?.get(col.key) ?? null;
                    return (
                      <td
                        key={col.key}
                        className="px-3 py-2.5 text-center border-border"
                      >
                        {cell ? (
                          <span
                            className={`inline-block text-[10px] font-mono uppercase tracking-wider px-2 py-0.5 rounded border ${
                              cell.level === "editor"
                                ? "text-amber-400 bg-amber-500/10 border-amber-500/20"
                                : "text-sky-400 bg-sky-500/10 border-sky-500/20"
                            }`}
                          >
                            {cell.level}
                          </span>
                        ) : (
                          <span className="text-[10px] font-mono text-border">
                            --
                          </span>
                        )}
                      </td>
                    );
                  })}
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      {/* Legend */}
      <div className="flex items-center gap-4 px-1">
        <span className="text-[10px] font-mono text-text-faint uppercase tracking-wider">
          Legend:
        </span>
        <div className="flex items-center gap-1.5">
          <span className="inline-block w-3 h-3 rounded border bg-sky-500/10 border-sky-500/20" />
          <span className="text-[10px] font-mono text-text-muted">Viewer</span>
        </div>
        <div className="flex items-center gap-1.5">
          <span className="inline-block w-3 h-3 rounded border bg-amber-500/10 border-amber-500/20" />
          <span className="text-[10px] font-mono text-text-muted">Editor</span>
        </div>
        <div className="flex items-center gap-1.5">
          <span className="text-[10px] font-mono text-border">--</span>
          <span className="text-[10px] font-mono text-text-muted">
            No grant
          </span>
        </div>
      </div>
    </div>
  );
}
