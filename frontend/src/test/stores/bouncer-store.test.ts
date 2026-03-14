import { describe, it, expect, beforeEach } from "vitest";
import { useBouncerStore } from "@/stores/bouncer-store";

beforeEach(() => {
  useBouncerStore.setState({
    selectedBouncers: [],
    teamFilter: undefined,
    topologyMode: "union",
  });
});

describe("useBouncerStore — initial state", () => {
  it("has empty selectedBouncers array", () => {
    expect(useBouncerStore.getState().selectedBouncers).toEqual([]);
  });

  it("has undefined teamFilter", () => {
    expect(useBouncerStore.getState().teamFilter).toBeUndefined();
  });

  it("defaults topologyMode to 'union'", () => {
    expect(useBouncerStore.getState().topologyMode).toBe("union");
  });
});

describe("useBouncerStore — toggleBouncer", () => {
  it("adds a bouncer when not already selected", () => {
    useBouncerStore.getState().toggleBouncer("SwitchPortBouncer");
    expect(useBouncerStore.getState().selectedBouncers).toContain("SwitchPortBouncer");
  });

  it("removes a bouncer that is already selected", () => {
    useBouncerStore.setState({ selectedBouncers: ["SwitchPortBouncer"] });
    useBouncerStore.getState().toggleBouncer("SwitchPortBouncer");
    expect(useBouncerStore.getState().selectedBouncers).not.toContain("SwitchPortBouncer");
  });

  it("adds multiple bouncers independently", () => {
    useBouncerStore.getState().toggleBouncer("SwitchPortBouncer");
    useBouncerStore.getState().toggleBouncer("DnsQueryBouncer");
    const { selectedBouncers } = useBouncerStore.getState();
    expect(selectedBouncers).toContain("SwitchPortBouncer");
    expect(selectedBouncers).toContain("DnsQueryBouncer");
    expect(selectedBouncers).toHaveLength(2);
  });

  it("removing one bouncer does not affect others", () => {
    useBouncerStore.setState({
      selectedBouncers: ["SwitchPortBouncer", "DnsQueryBouncer"],
    });
    useBouncerStore.getState().toggleBouncer("SwitchPortBouncer");
    expect(useBouncerStore.getState().selectedBouncers).not.toContain("SwitchPortBouncer");
    expect(useBouncerStore.getState().selectedBouncers).toContain("DnsQueryBouncer");
  });

  it("toggling the same bouncer twice restores empty state", () => {
    useBouncerStore.getState().toggleBouncer("SwitchPortBouncer");
    useBouncerStore.getState().toggleBouncer("SwitchPortBouncer");
    expect(useBouncerStore.getState().selectedBouncers).toHaveLength(0);
  });
});

describe("useBouncerStore — clearBouncers", () => {
  it("empties the selectedBouncers array", () => {
    useBouncerStore.setState({
      selectedBouncers: ["SwitchPortBouncer", "DnsQueryBouncer"],
    });
    useBouncerStore.getState().clearBouncers();
    expect(useBouncerStore.getState().selectedBouncers).toEqual([]);
  });

  it("is safe to call when already empty", () => {
    expect(() => useBouncerStore.getState().clearBouncers()).not.toThrow();
    expect(useBouncerStore.getState().selectedBouncers).toEqual([]);
  });
});

describe("useBouncerStore — setTeamFilter", () => {
  it("sets a team filter string", () => {
    useBouncerStore.getState().setTeamFilter("Dagger");
    expect(useBouncerStore.getState().teamFilter).toBe("Dagger");
  });

  it("clears team filter when set to undefined", () => {
    useBouncerStore.setState({ teamFilter: "Vault" });
    useBouncerStore.getState().setTeamFilter(undefined);
    expect(useBouncerStore.getState().teamFilter).toBeUndefined();
  });

  it("updates team filter from one team to another", () => {
    useBouncerStore.getState().setTeamFilter("Relay");
    useBouncerStore.getState().setTeamFilter("Prism");
    expect(useBouncerStore.getState().teamFilter).toBe("Prism");
  });
});

describe("useBouncerStore — setTopologyMode", () => {
  it("switches to 'intersection' mode", () => {
    useBouncerStore.getState().setTopologyMode("intersection");
    expect(useBouncerStore.getState().topologyMode).toBe("intersection");
  });

  it("switches back to 'union' mode", () => {
    useBouncerStore.setState({ topologyMode: "intersection" });
    useBouncerStore.getState().setTopologyMode("union");
    expect(useBouncerStore.getState().topologyMode).toBe("union");
  });
});
