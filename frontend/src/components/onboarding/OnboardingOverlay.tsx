import { useEffect, useMemo, useCallback, useRef } from "react";
import { useOnboardingStore } from "@/stores/onboarding-store";
import { useAuthStore } from "@/stores/auth-store";
import { useNavigationStore } from "@/stores/navigation-store";
import { isAdmin } from "@/lib/permissions";
import { getOnboardingSteps } from "./onboarding-steps";
import type { PanelPosition } from "./onboarding-steps";
import { SidebarSpotlight } from "./SidebarSpotlight";
import { SectionSpotlight } from "./SectionSpotlight";
import { SpotlightConnector } from "./SpotlightConnector";
import { OnboardingStepContent } from "./OnboardingStep";

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

  // Navigate to the relevant tab for each step
  useEffect(() => {
    if (!isActive || isExiting || !step?.navigateTo) return;
    setActiveTab(step.navigateTo);
  }, [isActive, isExiting, step?.navigateTo, setActiveTab]);

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

  const isCentered = step.panelPosition === "center" || isExiting;
  const hasSectionTarget = !isCentered && !isExiting && !!step.sectionTarget;
  const panelStyle = isExiting ? getPanelStyle("center") : getPanelStyle(step.panelPosition);

  const slideClass = direction === "forward"
    ? "slide-in-from-right-4"
    : "slide-in-from-left-4";

  const firstName = user?.display_name?.split(" ")[0] ?? "";
  const teamNames = user?.teams?.map((t) => t.name).join(", ");
  const roleLabel = user?.role ?? "";

  return (
    <div className="fixed inset-0 z-[60]">
      {/* Backdrop */}
      <div
        className={`absolute inset-0 transition-all duration-500 ease-out ${
          isCentered
            ? "bg-background/95 backdrop-blur-xl onboarding-hex-grid onboarding-scanline"
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
        <div className="bg-surface-raised border border-border rounded-2xl shadow-[0_0_60px_rgba(99,102,241,0.06),0_25px_50px_-12px_rgba(0,0,0,0.5)] overflow-hidden">
          {/* Data-stream top accent */}
          <div className="h-[2px] onboarding-border-flow" />

          {/* Animated content — remounts per step for direction-aware slide */}
          <OnboardingStepContent
            step={step}
            isCentered={isCentered}
            slideClass={slideClass}
            currentStep={currentStep}
            totalSteps={steps.length}
            firstName={firstName}
            teamNames={teamNames}
            roleLabel={roleLabel}
            hasUser={!!user}
          />

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
                  className="px-3.5 py-1.5 text-xs text-slate-400 hover:text-white border border-border-prominent hover:border-white/20 rounded-lg transition-all font-medium"
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
