import { useState, useEffect, useCallback } from "react";

/**
 * Hook that makes a scrollable container pannable via click-drag.
 * Returns a callback ref to attach to the scrollable container element.
 *
 * Uses a callback ref so it works correctly with conditionally rendered
 * elements (modals, etc.) that mount after the hook is first called.
 *
 * - Default cursor: grab
 * - While dragging: grabbing
 * - Ignores drags that start on interactive elements (buttons, links, inputs)
 */
export function usePannable<T extends HTMLElement = HTMLDivElement>() {
  const [el, setEl] = useState<T | null>(null);
  const ref = useCallback((node: T | null) => setEl(node), []);

  useEffect(() => {
    if (!el) return;

    let isPanning = false;
    let startX = 0;
    let startY = 0;
    let scrollLeft = 0;
    let scrollTop = 0;

    el.style.cursor = "grab";

    function onMouseDown(e: MouseEvent) {
      // Don't hijack clicks on interactive elements
      const target = e.target as HTMLElement;
      if (
        target.closest(
          "button, a, input, select, textarea, [role='button']",
        )
      )
        return;

      isPanning = true;
      startX = e.clientX;
      startY = e.clientY;
      scrollLeft = el!.scrollLeft;
      scrollTop = el!.scrollTop;
      el!.style.cursor = "grabbing";
      el!.style.userSelect = "none";
      e.preventDefault();
    }

    function onMouseMove(e: MouseEvent) {
      if (!isPanning) return;
      el!.scrollLeft = scrollLeft - (e.clientX - startX);
      el!.scrollTop = scrollTop - (e.clientY - startY);
    }

    function onMouseUp() {
      if (!isPanning) return;
      isPanning = false;
      el!.style.cursor = "grab";
      el!.style.removeProperty("user-select");
    }

    el.addEventListener("mousedown", onMouseDown);
    document.addEventListener("mousemove", onMouseMove);
    document.addEventListener("mouseup", onMouseUp);

    return () => {
      el.removeEventListener("mousedown", onMouseDown);
      document.removeEventListener("mousemove", onMouseMove);
      document.removeEventListener("mouseup", onMouseUp);
      el.style.removeProperty("cursor");
      el.style.removeProperty("user-select");
    };
  }, [el]);

  return ref;
}
