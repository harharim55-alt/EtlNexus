import { create } from "zustand";

const STORAGE_KEY_COMPLETED = "etlnexus:onboarding:completed";
const STORAGE_KEY_VERSION = "etlnexus:onboarding:version";
const ONBOARDING_VERSION = 1;

function readCompleted(): boolean {
  try {
    const version = localStorage.getItem(STORAGE_KEY_VERSION);
    return version === String(ONBOARDING_VERSION);
  } catch {
    return false;
  }
}

function persistCompleted(): void {
  try {
    localStorage.setItem(STORAGE_KEY_COMPLETED, "true");
    localStorage.setItem(STORAGE_KEY_VERSION, String(ONBOARDING_VERSION));
  } catch {
    // localStorage unavailable
  }
}

function clearCompleted(): void {
  try {
    localStorage.removeItem(STORAGE_KEY_COMPLETED);
    localStorage.removeItem(STORAGE_KEY_VERSION);
  } catch {
    // localStorage unavailable
  }
}

interface OnboardingState {
  isActive: boolean;
  isExiting: boolean;
  currentStep: number;
  hasCompleted: boolean;
  direction: "forward" | "backward";
  startOnboarding: () => void;
  nextStep: (totalSteps: number) => void;
  prevStep: () => void;
  goToStep: (step: number) => void;
  beginExit: () => void;
  finalizeExit: () => void;
  completeOnboarding: () => void;
  resetOnboarding: () => void;
}

export const useOnboardingStore = create<OnboardingState>((set) => ({
  isActive: false,
  isExiting: false,
  currentStep: 0,
  hasCompleted: readCompleted(),
  direction: "forward",

  startOnboarding: () =>
    set({ isActive: true, isExiting: false, currentStep: 0, direction: "forward" }),

  nextStep: (totalSteps) =>
    set((state) => {
      if (state.currentStep >= totalSteps - 1) {
        // Trigger CRT shutdown instead of instant close
        return { isExiting: true, direction: "forward" };
      }
      return { currentStep: state.currentStep + 1, direction: "forward" };
    }),

  prevStep: () =>
    set((state) => ({
      currentStep: Math.max(0, state.currentStep - 1),
      direction: "backward",
    })),

  goToStep: (step) =>
    set((state) => ({
      currentStep: step,
      direction: step > state.currentStep ? "forward" : "backward",
    })),

  beginExit: () => set({ isExiting: true }),

  finalizeExit: () => {
    persistCompleted();
    set({ isActive: false, isExiting: false, hasCompleted: true });
  },

  completeOnboarding: () => {
    // Trigger the CRT shutdown animation
    set({ isExiting: true });
  },

  resetOnboarding: () => {
    clearCompleted();
    set({ isActive: false, isExiting: false, currentStep: 0, hasCompleted: false, direction: "forward" });
  },
}));
