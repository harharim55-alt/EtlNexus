import { useSensorStore } from "@/stores/sensor-store";

const TEAM_COLORS: Record<string, { bg: string; text: string; border: string }> = {
  Dagger: {
    bg: "bg-indigo-500/15",
    text: "text-indigo-300",
    border: "border-indigo-500/30",
  },
  Vault: {
    bg: "bg-indigo-500/15",
    text: "text-indigo-300",
    border: "border-indigo-500/30",
  },
  Prism: {
    bg: "bg-indigo-500/15",
    text: "text-indigo-300",
    border: "border-indigo-500/30",
  },
  Relay: {
    bg: "bg-indigo-500/15",
    text: "text-indigo-300",
    border: "border-indigo-500/30",
  },
  Oasis: {
    bg: "bg-indigo-500/15",
    text: "text-indigo-300",
    border: "border-indigo-500/30",
  },
};

const DEFAULT_TEAM = {
  bg: "bg-indigo-500/15",
  text: "text-indigo-300",
  border: "border-indigo-500/30",
};

interface TeamFilterProps {
  teams: string[];
}

export function TeamFilter({ teams }: TeamFilterProps) {
  const teamFilter = useSensorStore((s) => s.teamFilter);
  const setTeamFilter = useSensorStore((s) => s.setTeamFilter);

  return (
    <div className="flex items-center gap-2 flex-wrap">
      <button
        type="button"
        onClick={() => setTeamFilter(undefined)}
        className={`text-[10px] font-mono px-3 py-1.5 rounded-full border transition-all cursor-pointer ${
          !teamFilter
            ? "text-teal-300 bg-teal-500/15 border-teal-500/30 shadow-[0_0_10px_rgba(45,212,191,0.15)]"
            : "text-slate-500 bg-white/[0.02] border-white/5 hover:border-white/15 hover:text-slate-400"
        }`}
      >
        All Teams
      </button>
      {teams.map((team) => {
        const colors = TEAM_COLORS[team] || DEFAULT_TEAM;
        const isActive = teamFilter === team;
        return (
          <button
            key={team}
            type="button"
            onClick={() => setTeamFilter(team)}
            className={`text-[10px] font-mono px-3 py-1.5 rounded-full border transition-all cursor-pointer ${
              isActive
                ? `${colors.text} ${colors.bg} ${colors.border} shadow-[0_0_10px_rgba(99,102,241,0.15)]`
                : "text-slate-500 bg-white/[0.02] border-white/5 hover:border-white/15 hover:text-slate-400"
            }`}
          >
            {team}
          </button>
        );
      })}
    </div>
  );
}
