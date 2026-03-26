import { Rocket } from "lucide-react";
import type { OnboardingStep as OnboardingStepType } from "./onboarding-steps";

/* ── Props ─────────────────────────────────────────────────────────── */

interface OnboardingStepContentProps {
  step: OnboardingStepType;
  isCentered: boolean;
  slideClass: string;
  currentStep: number;
  totalSteps: number;
  /** First name from user display_name (empty string if not available) */
  firstName: string;
  /** Comma-separated team names */
  teamNames: string | undefined;
  /** User role label */
  roleLabel: string;
  /** Whether the user object is available */
  hasUser: boolean;
}

/* ── Component ─────────────────────────────────────────────────────── */

export function OnboardingStepContent({
  step,
  isCentered,
  slideClass,
  currentStep,
  totalSteps,
  firstName,
  teamNames,
  roleLabel,
  hasUser,
}: OnboardingStepContentProps) {
  const Icon = step.icon;

  return (
    <div key={step.id} className={`animate-in fade-in ${slideClass} duration-200`}>
      {/* Step label */}
      <div className="px-6 pt-5 flex items-center justify-between">
        <span className="text-[10px] font-mono tracking-[0.2em] uppercase text-indigo-400/50">
          system briefing // step{" "}
          {String(currentStep + 1).padStart(2, "0")} of{" "}
          {String(totalSteps).padStart(2, "0")}
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
            {step.isWelcome && hasUser && (
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
  );
}
