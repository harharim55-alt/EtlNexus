import { useSensorStore } from "@/stores/sensor-store";

const TEAM_COLORS: Record<string, { bg: string; text: string; border: string }> = {
  "Infrastructure Ops": {
    bg: "bg-sky-500/10",
    text: "text-sky-400",
    border: "border-sky-500/20",
  },
  "Network Monitoring": {
    bg: "bg-violet-500/10",
    text: "text-violet-400",
    border: "border-violet-500/20",
  },
  "Security Engineering": {
    bg: "bg-rose-500/10",
    text: "text-rose-400",
    border: "border-rose-500/20",
  },
  "NOC Operations": {
    bg: "bg-amber-500/10",
    text: "text-amber-400",
    border: "border-amber-500/20",
  },
};

const DEFAULT_TEAM = {
  bg: "bg-slate-500/10",
  text: "text-slate-400",
  border: "border-slate-500/20",
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
                ? `${colors.text} ${colors.bg} ${colors.border}`
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
