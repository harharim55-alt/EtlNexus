import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip";

interface NavIconProps {
  active: boolean;
  onClick: () => void;
  icon: React.ReactNode;
  tooltip: string;
}

export function NavIcon({ active, onClick, icon, tooltip }: NavIconProps) {
  return (
    <Tooltip>
      <TooltipTrigger
        onClick={onClick}
        className={`p-3 rounded-xl transition-all duration-200 cursor-pointer ${
          active
            ? "bg-indigo-500/10 text-indigo-400 shadow-[inset_0_0_0_1px_rgba(99,102,241,0.2)]"
            : "text-slate-500 hover:bg-white/5 hover:text-slate-300"
        }`}
      >
        {icon}
      </TooltipTrigger>
      <TooltipContent
        side="right"
        className="bg-[#18181b] border-white/10 text-white text-xs font-medium"
      >
        {tooltip}
      </TooltipContent>
    </Tooltip>
  );
}
