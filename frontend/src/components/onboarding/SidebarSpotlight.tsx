import { useState, useEffect, useCallback } from "react";
import type { TabType } from "@/lib/constants";

interface SidebarSpotlightProps {
  target: TabType;
}

export function SidebarSpotlight({ target }: SidebarSpotlightProps) {
  const [rect, setRect] = useState<DOMRect | null>(null);

  const updatePosition = useCallback(() => {
    const el = document.querySelector(`[data-nav-id="${target}"]`);
    if (el) {
      setRect(el.getBoundingClientRect());
    }
  }, [target]);

  useEffect(() => {
    updatePosition();

    const observer = new ResizeObserver(updatePosition);
    observer.observe(document.body);

    window.addEventListener("resize", updatePosition);
    return () => {
      observer.disconnect();
      window.removeEventListener("resize", updatePosition);
    };
  }, [updatePosition]);

  if (!rect) return null;

  const padding = 6;

  return (
    <div
      className="fixed z-[59] rounded-xl border-2 border-indigo-500/50 onboarding-spotlight-ring pointer-events-none"
      style={{
        top: rect.top - padding,
        left: rect.left - padding,
        width: rect.width + padding * 2,
        height: rect.height + padding * 2,
      }}
    />
  );
}
