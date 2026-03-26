import { useState } from "react";
import { useCreateGrant } from "@/hooks/use-admin";

/* ── Types ────────────────────────────────────────────────────────── */

export type GrantType = "pipeline" | "team";
export type GranteeType = "team" | "user";

export interface GrantFormState {
  showForm: boolean;
  granteeType: GranteeType;
  granteeTeamId: string;
  granteeUserId: string;
  grantType: GrantType;
  pipelineId: string;
  sourceTeamId: string;
  grantLevel: "viewer" | "editor";
}

/* ── Hook ─────────────────────────────────────────────────────────── */

export function useGrantForm() {
  const [showForm, setShowForm] = useState(false);
  const [granteeType, setGranteeType] = useState<GranteeType>("team");
  const [granteeTeamId, setGranteeTeamId] = useState("");
  const [granteeUserId, setGranteeUserId] = useState("");
  const [grantType, setGrantType] = useState<GrantType>("pipeline");
  const [pipelineId, setPipelineId] = useState("");
  const [sourceTeamId, setSourceTeamId] = useState("");
  const [grantLevel, setGrantLevel] = useState<"viewer" | "editor">("viewer");

  const createGrant = useCreateGrant();

  const resetForm = () => {
    setGranteeType("team");
    setGranteeTeamId("");
    setGranteeUserId("");
    setGrantType("pipeline");
    setPipelineId("");
    setSourceTeamId("");
    setGrantLevel("viewer");
    setShowForm(false);
  };

  const handleCreate = () => {
    const hasGrantee = granteeType === "team" ? granteeTeamId : granteeUserId;
    const hasTarget = grantType === "pipeline" ? pipelineId : sourceTeamId;
    if (!hasGrantee || !hasTarget) return;

    const body = {
      ...(granteeType === "team"
        ? { grantee_team_id: granteeTeamId }
        : { grantee_user_id: granteeUserId }),
      ...(grantType === "pipeline"
        ? { pipeline_id: pipelineId }
        : { source_team_id: sourceTeamId }),
      grant_level: grantLevel,
    };

    createGrant.mutate(body, { onSuccess: resetForm });
  };

  const handleGranteeTypeChange = (type: GranteeType) => {
    setGranteeType(type);
    setGranteeTeamId("");
    setGranteeUserId("");
  };

  return {
    // State
    showForm,
    granteeType,
    granteeTeamId,
    granteeUserId,
    grantType,
    pipelineId,
    sourceTeamId,
    grantLevel,
    // Mutation
    createGrant,
    // Actions
    setShowForm,
    setGranteeTeamId,
    setGranteeUserId,
    setGrantType,
    setPipelineId,
    setSourceTeamId,
    setGrantLevel,
    handleGranteeTypeChange,
    resetForm,
    handleCreate,
  };
}
