import { describe, it, expect } from "vitest";
import { formatDuration } from "@/lib/format";

describe("formatDuration", () => {
  it("formats seconds under a minute", () => {
    expect(formatDuration(45)).toBe("45s");
    expect(formatDuration(0)).toBe("0s");
    expect(formatDuration(59.4)).toBe("59s");
  });

  it("formats minutes", () => {
    expect(formatDuration(60)).toBe("1m");
    expect(formatDuration(90)).toBe("1m 30s");
    expect(formatDuration(3599)).toBe("59m 59s");
  });

  it("formats hours", () => {
    expect(formatDuration(3600)).toBe("1h");
    expect(formatDuration(3660)).toBe("1h 1m");
    expect(formatDuration(7200)).toBe("2h");
    expect(formatDuration(5400)).toBe("1h 30m");
  });

  it("rounds seconds", () => {
    expect(formatDuration(0.4)).toBe("0s");
    expect(formatDuration(0.6)).toBe("1s");
    expect(formatDuration(61.7)).toBe("1m 2s");
  });
});
