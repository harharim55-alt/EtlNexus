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
            : "text-text-muted hover:bg-hover-bg hover:text-text-primary"
        }`}
      >
        {icon}
      </TooltipTrigger>
      <TooltipContent
        side="right"
        className="bg-card border-border-prominent text-foreground text-xs font-medium"
      >
        {tooltip}
      </TooltipContent>
    </Tooltip>
  );
}
