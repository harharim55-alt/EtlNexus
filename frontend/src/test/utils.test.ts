import { describe, it, expect } from "vitest";
import { isApiPipeline } from "@/lib/utils";

describe("isApiPipeline", () => {
  it('returns true for pipeline_type "api"', () => {
    expect(isApiPipeline("api")).toBe(true);
  });

  it('returns false for pipeline_type "etl"', () => {
    expect(isApiPipeline("etl")).toBe(false);
  });

  it("returns false for null and undefined", () => {
    expect(isApiPipeline(null)).toBe(false);
    expect(isApiPipeline(undefined)).toBe(false);
  });

  it("returns false for empty string", () => {
    expect(isApiPipeline("")).toBe(false);
  });

  it("returns false for arbitrary strings", () => {
    expect(isApiPipeline("API")).toBe(false);
    expect(isApiPipeline("Api")).toBe(false);
    expect(isApiPipeline("Network APIs")).toBe(false);
  });
});
