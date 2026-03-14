import { describe, it, expect } from "vitest";
import { getStatusStyle, STATUS_CONFIG } from "@/lib/status-config";

describe("getStatusStyle", () => {
  it("returns correct style for known statuses", () => {
    const success = getStatusStyle("success");
    expect(success.label).toBe("Success");
    expect(success.dot).toContain("bg-emerald");

    const failed = getStatusStyle("failed");
    expect(failed.label).toBe("Failed");
    expect(failed.dot).toContain("bg-rose");
  });

  it("returns 'unknown' style for unrecognized statuses", () => {
    const unknown = getStatusStyle("nonexistent_status");
    expect(unknown.label).toBe("Unknown");
    expect(unknown).toBe(STATUS_CONFIG.unknown);
  });

  it("returns correct style for upstream_failed", () => {
    const style = getStatusStyle("upstream_failed");
    expect(style.label).toBe("Upstream Failed");
    expect(style.dot).toContain("bg-orange");
  });

  it("returns running style with animate-pulse", () => {
    const style = getStatusStyle("running");
    expect(style.dot).toContain("animate-pulse");
  });

  it("has all expected status keys", () => {
    const expected = [
      "success", "failed", "upstream_failed", "running", "queued",
      "skipped", "up_for_retry", "deferred", "scheduled",
      "up_for_reschedule", "removed", "restarting", "no_status", "unknown",
    ];
    for (const key of expected) {
      expect(STATUS_CONFIG).toHaveProperty(key);
    }
  });
});
