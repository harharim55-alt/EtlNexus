import { useEffect, useMemo, useCallback, useRef } from "react";
import { Rocket } from "lucide-react";
import { useQueryClient } from "@tanstack/react-query";
import { useOnboardingStore } from "@/stores/onboarding-store";
import { useAuthStore } from "@/stores/auth-store";
import { useNavigationStore } from "@/stores/navigation-store";
import { usePipelineStore } from "@/stores/pipeline-store";
import { useBouncerStore } from "@/stores/bouncer-store";
import { isAdmin } from "@/lib/permissions";
import { isApiPipeline } from "@/lib/utils";
import { getOnboardingSteps } from "./onboarding-steps";
import type { PanelPosition } from "./onboarding-steps";
import type { PipelineListItem } from "@/types/pipeline";
import type { BouncerListResponse } from "@/types/bouncer";
import { fetchBouncers } from "@/api/bouncers";
import { SidebarSpotlight } from "./SidebarSpotlight";
import { SectionSpotlight } from "./SectionSpotlight";
import { SpotlightConnector } from "./SpotlightConnector";

/** Compute CSS position styles for smooth panel movement. */
function getPanelStyle(position: PanelPosition): React.CSSProperties {
  switch (position) {
    case "center":
      return {
        top: "50%",
        left: "50%",
        transform: "translate(-50%, -50%)",
        width: 720,
        maxWidth: "calc(100vw - 48px)",
      };
    case "right":
      return {
        top: "50%",
        left: "calc(100vw - 480px - 28px)",
        transform: "translate(0%, -50%)",
        width: 460,
      };
    case "bottom-left":
      return {
        top: "calc(100vh - 28px)",
        left: "104px",
        transform: "translate(0%, -100%)",
        width: 480,
      };
    case "bottom-right":
      return {
        top: "calc(100vh - 28px)",
        left: "calc(100vw - 520px - 28px)",
        transform: "translate(0%, -100%)",
        width: 500,
      };
  }
}

export function OnboardingOverlay() {
  const {
    isActive, isExiting, currentStep, hasCompleted, direction,
    startOnboarding, nextStep, prevStep, goToStep, completeOnboarding, finalizeExit,
  } = useOnboardingStore();
  const user = useAuthStore((s) => s.user);
  const setActiveTab = useNavigationStore((s) => s.setActiveTab);
  const selectedPipelineId = usePipelineStore((s) => s.selectedPipelineId);
  const setSelectedPipelineId = usePipelineStore((s) => s.setSelectedPipelineId);
  const selectedBouncers = useBouncerStore((s) => s.selectedBouncers);
  const toggleBouncer = useBouncerStore((s) => s.toggleBouncer);
  const queryClient = useQueryClient();
  const admin = isAdmin(user);
  const panelRef = useRef<HTMLDivElement>(null);

  const steps = useMemo(() => getOnboardingSteps(admin), [admin]);
  const step = steps[currentStep];
  const isFirstStep = currentStep === 0;
  const isLastStep = currentStep === steps.length - 1;

  // Auto-start on first visit
  useEffect(() => {
    if (user && !hasCompleted && !isActive) {
      startOnboarding();
    }
  }, [user, hasCompleted, isActive, startOnboarding]);

  // Navigate to the relevant tab + auto-select ETL pipeline for workspace step
  useEffect(() => {
    if (!isActive || isExiting || !step?.navigateTo) return;
    setActiveTab(step.navigateTo);

    // Auto-select first non-API pipeline for catalog/workspace steps
    if ((step.id === "catalog" || step.id === "workspace")) {
      const cached = queryClient.getQueryData<{
        pages: Array<{ items: PipelineListItem[]; total: number }>;
      }>(["pipelines", ""]);
      if (cached?.pages) {
        const allPipelines = cached.pages.flatMap((p) => p.items);
        const currentPipeline = selectedPipelineId
          ? allPipelines.find((p) => p.id === selectedPipelineId)
          : null;
        // Force non-API selection if nothing selected or current is API
        if (!currentPipeline || isApiPipeline(currentPipeline.category)) {
          const etlPipeline = allPipelines.find(
            (p) => !isApiPipeline(p.category),
          );
          // Fallback to first pipeline if all are API
          const target = etlPipeline ?? allPipelines[0];
          if (target) {
            setSelectedPipelineId(target.id);
          }
        }
      }
    }

    // Prefetch + auto-select two bouncers with intersection mode for the bouncers step
    if (step.id === "bouncers" && selectedBouncers.length === 0) {
      const selectBouncers = (data: BouncerListResponse) => {
        const store = useBouncerStore.getState();
        if (store.selectedBouncers.length > 0) return;
        const bouncers = data.bouncers;
        if (bouncers.length === 0) return;
        if (bouncers.length === 1) {
          store.toggleBouncer(bouncers[0].bouncer_name);
          return;
        }
        // Single-pass: find a pair sharing a dag_id for intersection mode
        const dagToBouncer = new Map<string, string>();
        let picked: [string, string] | null = null;
        for (const bouncer of bouncers) {
          for (const dagId of bouncer.dag_ids) {
            const other = dagToBouncer.get(dagId);
            if (other && other !== bouncer.bouncer_name) {
              picked = [other, bouncer.bouncer_name];
              break;
            }
            dagToBouncer.set(dagId, bouncer.bouncer_name);
          }
          if (picked) break;
        }
        if (picked) {
          store.toggleBouncer(picked[0]);
          store.toggleBouncer(picked[1]);
          store.setTopologyMode("intersection");
        } else {
          // No intersection found — pick first two with union
          store.toggleBouncer(bouncers[0].bouncer_name);
          store.toggleBouncer(bouncers[1].bouncer_name);
          store.setTopologyMode("union");
        }
      };

      const cached = queryClient.getQueryData<BouncerListResponse>(["bouncers", "all"]);
      if (cached?.bouncers?.length) {
        selectBouncers(cached);
      } else {
        queryClient.prefetchQuery({
          queryKey: ["bouncers", "all"],
          queryFn: () => fetchBouncers(),
        }).then(() => {
          const data = queryClient.getQueryData<BouncerListResponse>(["bouncers", "all"]);
          if (data) selectBouncers(data);
        });
      }
    }
  }, [isActive, isExiting, currentStep, step?.navigateTo, step?.id, setActiveTab, selectedPipelineId, setSelectedPipelineId, selectedBouncers.length, toggleBouncer, queryClient]);

  // Auto-scroll the bento workspace on the workspace step
  useEffect(() => {
    if (!isActive || isExiting || step?.id !== "workspace") return;

    let rafId: number;
    let scrollEl: HTMLElement | null = null;

    // Wait for content to load before starting scroll
    const startTimer = setTimeout(() => {
      scrollEl = document.querySelector('[data-section="bento-workspace"]');
      if (!scrollEl || scrollEl.scrollHeight <= scrollEl.clientHeight) return;

      const speed = 0.4; // px per frame (~24px/s at 60fps)
      const tick = () => {
        if (!scrollEl) return;
        // Stop near the bottom
        if (scrollEl.scrollTop + scrollEl.clientHeight >= scrollEl.scrollHeight - 10) return;
        scrollEl.scrollTop += speed;
        rafId = requestAnimationFrame(tick);
      };
      rafId = requestAnimationFrame(tick);
    }, 1200);

    return () => {
      clearTimeout(startTimer);
      cancelAnimationFrame(rafId);
      // Reset scroll position when leaving
      if (scrollEl) scrollEl.scrollTop = 0;
    };
  }, [isActive, isExiting, step?.id]);

  // Keyboard navigation
  const handleKeyDown = useCallback(
    (e: KeyboardEvent) => {
      if (!isActive || isExiting) return;
      if (e.key === "ArrowRight" || e.key === "Enter") {
        e.preventDefault();
        if (isLastStep) {
          completeOnboarding();
        } else {
          nextStep(steps.length);
        }
      } else if (e.key === "ArrowLeft") {
        e.preventDefault();
        prevStep();
      } else if (e.key === "Escape") {
        e.preventDefault();
        completeOnboarding();
      }
    },
    [isActive, isExiting, isLastStep, completeOnboarding, nextStep, prevStep, steps.length],
  );

  useEffect(() => {
    if (!isActive) return;
    document.addEventListener("keydown", handleKeyDown);
    document.body.style.overflow = "hidden";
    return () => {
      document.removeEventListener("keydown", handleKeyDown);
      document.body.style.overflow = "";
    };
  }, [isActive, handleKeyDown]);

  // Handle CRT shutdown animation end
  const handleShutdownEnd = useCallback(
    (e: React.AnimationEvent) => {
      if (e.animationName === "onboarding-shutdown") {
        finalizeExit();
      }
    },
    [finalizeExit],
  );

  if (!isActive || !step) return null;

  const Icon = step.icon;
  const isCentered = step.panelPosition === "center" || isExiting;
  const hasSectionTarget = !isCentered && !isExiting && !!step.sectionTarget;
  // Snap to center for the CRT shutdown animation
  const panelStyle = isExiting ? getPanelStyle("center") : getPanelStyle(step.panelPosition);

  // Direction-aware slide class for step content transitions
  const slideClass = direction === "forward"
    ? "slide-in-from-right-4"
    : "slide-in-from-left-4";

  // Personalized welcome: extract first name + context
  const firstName = user?.display_name?.split(" ")[0] ?? "";
  const teamNames = user?.teams?.map((t) => t.name).join(", ");
  const roleLabel = user?.role ?? "";

  return (
    <div className="fixed inset-0 z-[60]">
      {/* Backdrop */}
      <div
        className={`absolute inset-0 transition-all duration-500 ease-out ${
          isCentered
            ? "bg-[#09090b]/95 backdrop-blur-xl onboarding-hex-grid onboarding-scanline"
            : hasSectionTarget
              ? "bg-transparent"
              : "bg-black/50 backdrop-blur-[2px]"
        } ${isExiting ? "onboarding-backdrop-exit" : ""}`}
      />

      {/* Section spotlight cutout */}
      {hasSectionTarget && step.sectionTarget && (
        <SectionSpotlight sectionTarget={step.sectionTarget} />
      )}

      {/* Spark burst after CRT dot collapses */}
      {isExiting && <div className="onboarding-spark" />}

      {/* Sidebar spotlight */}
      {!isExiting && step.spotlightTarget && <SidebarSpotlight target={step.spotlightTarget} />}

      {/* Connector line from panel to sidebar target */}
      {!isExiting && !isCentered && step.spotlightTarget && (
        <SpotlightConnector target={step.spotlightTarget} panelRef={panelRef} />
      )}

      {/* Panel container — smooth position transitions + CRT shutdown */}
      <div
        ref={panelRef}
        className={`absolute z-[61] ${isExiting ? "onboarding-shutdown" : ""}`}
        style={{
          ...panelStyle,
          transition: "top 500ms cubic-bezier(0.4, 0, 0.2, 1), left 500ms cubic-bezier(0.4, 0, 0.2, 1), transform 500ms cubic-bezier(0.4, 0, 0.2, 1), width 500ms cubic-bezier(0.4, 0, 0.2, 1)",
        }}
        onAnimationEnd={handleShutdownEnd}
      >
        {/* HUD corner brackets */}
        <div className="absolute -top-2 -left-2 w-5 h-5 border-t-2 border-l-2 border-indigo-500/30 rounded-tl-sm" />
        <div className="absolute -top-2 -right-2 w-5 h-5 border-t-2 border-r-2 border-indigo-500/30 rounded-tr-sm" />
        <div className="absolute -bottom-2 -left-2 w-5 h-5 border-b-2 border-l-2 border-indigo-500/30 rounded-bl-sm" />
        <div className="absolute -bottom-2 -right-2 w-5 h-5 border-b-2 border-r-2 border-indigo-500/30 rounded-br-sm" />

        {/* Card */}
        <div className="bg-[#111116] border border-white/[0.08] rounded-2xl shadow-[0_0_60px_rgba(99,102,241,0.06),0_25px_50px_-12px_rgba(0,0,0,0.5)] overflow-hidden">
          {/* Data-stream top accent */}
          <div className="h-[2px] onboarding-border-flow" />

          {/* Animated content — remounts per step for direction-aware slide */}
          <div key={step.id} className={`animate-in fade-in ${slideClass} duration-200`}>
            {/* Step label */}
            <div className="px-6 pt-5 flex items-center justify-between">
              <span className="text-[10px] font-mono tracking-[0.2em] uppercase text-indigo-400/50">
                system briefing // step{" "}
                {String(currentStep + 1).padStart(2, "0")} of{" "}
                {String(steps.length).padStart(2, "0")}
              </span>
              {step.adminOnly && (
                <span className="text-[9px] font-mono tracking-[0.15em] uppercase text-rose-400/60 bg-rose-500/10 border border-rose-500/15 px-2 py-0.5 rounded">
                  admin
                </span>
              )}
            </div>

            {/* Main content */}
            <div className="px-6 pt-4 pb-5">
              <div className="flex items-start gap-4">
                {/* Icon */}
                <div className={`p-3 rounded-xl ${step.iconBg} border ${step.iconBorder} shrink-0`}>
                  <Icon className={`${isCentered ? "size-7" : "size-5"} ${step.iconText}`} />
                </div>

                {/* Text content */}
                <div className="flex-1 min-w-0">
                  {/* Personalized welcome title */}
                  {step.isWelcome && firstName ? (
                    <h2 className="text-2xl font-bold text-white tracking-tight onboarding-typewriter">
                      Welcome, {firstName}
                    </h2>
                  ) : (
                    <h2
                      className={`${isCentered ? "text-2xl" : "text-xl"} font-bold text-white tracking-tight`}
                    >
                      {step.title}
                    </h2>
                  )}

                  <p className="text-[11px] font-mono text-slate-600 mt-1 tracking-wide">
                    {step.subtitle}
                  </p>

                  {/* Personalized context badge for welcome step */}
                  {step.isWelcome && user && (
                    <div className="flex items-center gap-2 mt-2.5">
                      <span className="text-[10px] font-mono text-indigo-400/70 bg-indigo-500/8 border border-indigo-500/15 px-2 py-0.5 rounded">
                        {roleLabel}
                      </span>
                      {teamNames && (
                        <>
                          <span className="text-slate-700 text-[10px]">/</span>
                          <span className="text-[10px] font-mono text-slate-500">
                            {teamNames}
                          </span>
                        </>
                      )}
                    </div>
                  )}

                  <p className={`${isCentered ? "text-sm" : "text-[13px]"} text-slate-400 leading-relaxed mt-3`}>
                    {step.description}
                  </p>

                  {/* Feature bullets */}
                  {step.features && (
                    <ul className="mt-4 space-y-2">
                      {step.features.map((feature, i) => (
                        <li
                          key={i}
                          className={`flex items-center gap-2.5 ${isCentered ? "text-[13px]" : "text-xs"} text-slate-300 onboarding-stagger-item`}
                          style={{ animationDelay: `${150 + i * 70}ms` }}
                        >
                          <span className={`w-1.5 h-1.5 rounded-full ${step.dotColor} shrink-0`} />
                          {feature}
                        </li>
                      ))}
                    </ul>
                  )}

                  {/* Final step decoration */}
                  {step.isFinal && (
                    <div className="mt-5 flex items-center gap-3 text-emerald-400/80">
                      <div className="w-8 h-[1px] bg-emerald-500/30" />
                      <Rocket className="size-4" />
                      <span className="text-xs font-mono tracking-wider uppercase">
                        All systems operational
                      </span>
                      <div className="flex-1 h-[1px] bg-emerald-500/30" />
                    </div>
                  )}
                </div>
              </div>
            </div>
          </div>

          {/* Separator */}
          <div className="h-[1px] bg-white/[0.06]" />

          {/* Navigation bar */}
          <div className="px-6 py-3 flex items-center justify-between bg-white/[0.015]">
            {/* Progress dots */}
            <div className="flex items-center gap-1.5">
              {steps.map((_, i) => (
                <button
                  key={i}
                  onClick={() => goToStep(i)}
                  disabled={isExiting}
                  className={`h-2 rounded-full transition-all duration-300 cursor-pointer hover:opacity-80 ${
                    i === currentStep
                      ? "w-6 bg-indigo-400"
                      : i < currentStep
                        ? "w-2 bg-indigo-500/40"
                        : "w-2 bg-white/10"
                  }`}
                  aria-label={`Go to step ${i + 1}`}
                />
              ))}
            </div>

            {/* Keyboard hints */}
            <span className="text-[10px] font-mono text-slate-700 hidden lg:block select-none">
              &larr; &rarr; navigate &middot; Esc skip
            </span>

            {/* Buttons */}
            <div className="flex items-center gap-2.5">
              {!isLastStep && (
                <button
                  onClick={completeOnboarding}
                  disabled={isExiting}
                  className="text-[11px] text-slate-600 hover:text-slate-400 font-mono transition-colors tracking-wide"
                >
                  Skip
                </button>
              )}
              {!isFirstStep && (
                <button
                  onClick={prevStep}
                  disabled={isExiting}
                  className="px-3.5 py-1.5 text-xs text-slate-400 hover:text-white border border-white/10 hover:border-white/20 rounded-lg transition-all font-medium"
                >
                  Previous
                </button>
              )}
              {isLastStep ? (
                <button
                  onClick={completeOnboarding}
                  disabled={isExiting}
                  className="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white text-sm font-medium rounded-lg transition-colors shadow-lg shadow-indigo-500/20"
                >
                  Launch Command Center
                </button>
              ) : (
                <button
                  onClick={() => nextStep(steps.length)}
                  disabled={isExiting}
                  className="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-medium rounded-lg transition-colors shadow-lg shadow-indigo-500/20"
                >
                  Continue
                </button>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
