import { useQuery } from "@tanstack/react-query";
import { fetchBouncers, fetchBouncerTopology } from "@/api/bouncers";

export function useBouncers(team?: string) {
  return useQuery({
    queryKey: ["bouncers", team ?? "all"],
    queryFn: () => fetchBouncers(team),
    staleTime: 5 * 60_000,
    refetchInterval: 5 * 60_000,
  });
}

export function useBouncerTopology(bouncerNames: string[], mode: string = "union") {
  return useQuery({
    queryKey: ["bouncer-topology", ...bouncerNames.sort(), mode],
    queryFn: () => fetchBouncerTopology(bouncerNames, mode),
    enabled: bouncerNames.length > 0,
    staleTime: 30_000,
    refetchInterval: 60_000,
  });
}
