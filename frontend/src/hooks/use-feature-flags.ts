import { useQuery } from "@tanstack/react-query";
import { fetchFeatureFlags, checkFeatureFlag } from "@/api/feature-flags";

export function useFeatureFlags() {
  return useQuery({
    queryKey: ["feature-flags"],
    queryFn: fetchFeatureFlags,
    staleTime: 10 * 60_000,
  });
}

export function useFeatureFlagCheck(flagName: string) {
  return useQuery({
    queryKey: ["feature-flag-check", flagName],
    queryFn: () => checkFeatureFlag(flagName),
    staleTime: 10 * 60_000,
  });
}
