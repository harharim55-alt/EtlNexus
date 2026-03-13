import { useState, useEffect, useCallback, useRef } from "react";

interface SectionSpotlightProps {
  sectionTarget: string;
}

/**
 * Creates a box-shadow cutout that reveals the target content section
 * while darkening the rest of the viewport.
 */
export function SectionSpotlight({ sectionTarget }: SectionSpotlightProps) {
  const [rect, setRect] = useState<DOMRect | null>(null);
  const rafRef = useRef<number>(0);

  const updatePosition = useCallback(() => {
    const el = document.querySelector(`[data-section="${sectionTarget}"]`);
    if (el) {
      setRect(el.getBoundingClientRect());
    } else {
      setRect(null);
    }
  }, [sectionTarget]);

  useEffect(() => {
    // Reset immediately to avoid stale position flash on target change
    setRect(null);

    // Delay measurement to let tab switch + content mount settle
    const timer = setTimeout(updatePosition, 500);

    const observer = new ResizeObserver(() => {
      cancelAnimationFrame(rafRef.current);
      rafRef.current = requestAnimationFrame(updatePosition);
    });
    observer.observe(document.body);

    window.addEventListener("resize", updatePosition);
    return () => {
      clearTimeout(timer);
      cancelAnimationFrame(rafRef.current);
      observer.disconnect();
      window.removeEventListener("resize", updatePosition);
    };
  }, [updatePosition]);

  if (!rect) return null;

  const padding = 2;

  return (
    <div
      className="fixed z-[59] pointer-events-none onboarding-section-spotlight"
      style={{
        top: rect.top - padding,
        left: rect.left - padding,
        width: rect.width + padding * 2,
        height: rect.height + padding * 2,
        borderRadius: 12,
        border: "1px solid rgba(99, 102, 241, 0.12)",
        boxShadow: "0 0 0 9999px rgba(0, 0, 0, 0.7)",
        transition:
          "top 500ms cubic-bezier(0.4, 0, 0.2, 1), left 500ms cubic-bezier(0.4, 0, 0.2, 1), width 500ms cubic-bezier(0.4, 0, 0.2, 1), height 500ms cubic-bezier(0.4, 0, 0.2, 1)",
      }}
    />
  );
}
