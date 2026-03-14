import { describe, it, expect, beforeEach } from "vitest";
import { useDateRangeStore } from "@/stores/date-range-store";

beforeEach(() => {
  // Reset to the default 30d preset
  useDateRangeStore.getState().setPreset("30d");
});

describe("useDateRangeStore — initial state", () => {
  it("defaults to '30d' preset", () => {
    expect(useDateRangeStore.getState().preset).toBe("30d");
  });

  it("has a non-empty dateFrom string", () => {
    expect(useDateRangeStore.getState().dateFrom).toBeTruthy();
  });

  it("has a non-empty dateTo string", () => {
    expect(useDateRangeStore.getState().dateTo).toBeTruthy();
  });

  it("dateFrom is earlier than dateTo", () => {
    const { dateFrom, dateTo } = useDateRangeStore.getState();
    expect(new Date(dateFrom).getTime()).toBeLessThan(new Date(dateTo).getTime());
  });

  it("dateFrom is approximately 30 days before dateTo", () => {
    const { dateFrom, dateTo } = useDateRangeStore.getState();
    const diffMs = new Date(dateTo).getTime() - new Date(dateFrom).getTime();
    const thirtyDaysMs = 30 * 24 * 60 * 60 * 1000;
    // Allow 1 second tolerance for test execution time
    expect(Math.abs(diffMs - thirtyDaysMs)).toBeLessThan(1000);
  });
});

describe("useDateRangeStore — setPreset", () => {
  it("switches to '24h' and updates range", () => {
    useDateRangeStore.getState().setPreset("24h");
    const { preset, dateFrom, dateTo } = useDateRangeStore.getState();
    expect(preset).toBe("24h");
    const diffMs = new Date(dateTo).getTime() - new Date(dateFrom).getTime();
    const twentyFourHoursMs = 24 * 60 * 60 * 1000;
    expect(Math.abs(diffMs - twentyFourHoursMs)).toBeLessThan(1000);
  });

  it("switches to '7d' and updates range", () => {
    useDateRangeStore.getState().setPreset("7d");
    const { preset, dateFrom, dateTo } = useDateRangeStore.getState();
    expect(preset).toBe("7d");
    const diffMs = new Date(dateTo).getTime() - new Date(dateFrom).getTime();
    const sevenDaysMs = 7 * 24 * 60 * 60 * 1000;
    expect(Math.abs(diffMs - sevenDaysMs)).toBeLessThan(1000);
  });

  it("switches to '90d' and updates range", () => {
    useDateRangeStore.getState().setPreset("90d");
    const { preset, dateFrom, dateTo } = useDateRangeStore.getState();
    expect(preset).toBe("90d");
    const diffMs = new Date(dateTo).getTime() - new Date(dateFrom).getTime();
    const ninetyDaysMs = 90 * 24 * 60 * 60 * 1000;
    expect(Math.abs(diffMs - ninetyDaysMs)).toBeLessThan(1000);
  });

  it("dateFrom and dateTo are valid ISO strings after setPreset", () => {
    useDateRangeStore.getState().setPreset("7d");
    const { dateFrom, dateTo } = useDateRangeStore.getState();
    expect(() => new Date(dateFrom)).not.toThrow();
    expect(() => new Date(dateTo)).not.toThrow();
    expect(new Date(dateFrom).toISOString()).toBe(dateFrom);
    expect(new Date(dateTo).toISOString()).toBe(dateTo);
  });
});

describe("useDateRangeStore — setCustomRange", () => {
  it("sets preset to 'custom' with provided from/to", () => {
    const from = "2026-01-01T00:00:00.000Z";
    const to = "2026-03-01T00:00:00.000Z";
    useDateRangeStore.getState().setCustomRange(from, to);
    const state = useDateRangeStore.getState();
    expect(state.preset).toBe("custom");
    expect(state.dateFrom).toBe(from);
    expect(state.dateTo).toBe(to);
  });

  it("overwrites a previous preset with custom values", () => {
    useDateRangeStore.getState().setPreset("7d");
    const from = "2025-12-01T00:00:00.000Z";
    const to = "2025-12-31T00:00:00.000Z";
    useDateRangeStore.getState().setCustomRange(from, to);
    expect(useDateRangeStore.getState().preset).toBe("custom");
    expect(useDateRangeStore.getState().dateFrom).toBe(from);
    expect(useDateRangeStore.getState().dateTo).toBe(to);
  });
});
