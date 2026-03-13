interface Props {
  name: string;
  size?: "sm" | "md" | "lg";
}

const SIZE_CLASSES = {
  sm: "size-7 text-[10px] rounded-md",
  md: "size-8 text-[11px] rounded-lg",
  lg: "size-9 text-[11px] rounded-lg",
};

export function UserInitials({ name, size = "md" }: Props) {
  const initials = name
    .split(" ")
    .map((w) => w[0])
    .join("")
    .toUpperCase()
    .slice(0, 2);
  return (
    <div
      className={`${SIZE_CLASSES[size]} bg-indigo-500/10 border border-indigo-500/20 flex items-center justify-center font-semibold text-indigo-400 select-none shrink-0`}
    >
      {initials}
    </div>
  );
}
