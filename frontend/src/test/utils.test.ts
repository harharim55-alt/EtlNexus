import { describe, it, expect } from "vitest";
import { isApiPipeline } from "@/lib/utils";

describe("isApiPipeline", () => {
  it("returns true for category containing 'api' (case-insensitive)", () => {
    expect(isApiPipeline("Network APIs")).toBe(true);
    expect(isApiPipeline("api")).toBe(true);
    expect(isApiPipeline("API")).toBe(true);
    expect(isApiPipeline("Some Api Category")).toBe(true);
  });

  it("returns false for categories not containing 'api'", () => {
    expect(isApiPipeline("Network Infrastructure")).toBe(false);
    expect(isApiPipeline("Transit/Peering")).toBe(false);
    expect(isApiPipeline("DNS/Resolution")).toBe(false);
  });

  it("returns false for null and undefined", () => {
    expect(isApiPipeline(null)).toBe(false);
    expect(isApiPipeline(undefined)).toBe(false);
  });

  it("returns false for empty string", () => {
    expect(isApiPipeline("")).toBe(false);
  });
});
