import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { ErrorState } from "@/components/shared/ErrorState";

describe("ErrorState — rendering", () => {
  it("renders default message when no message prop given", () => {
    render(<ErrorState />);
    expect(screen.getByText("Something went wrong")).toBeInTheDocument();
  });

  it("renders custom error message", () => {
    render(<ErrorState message="Failed to load pipeline details" />);
    expect(screen.getByText("Failed to load pipeline details")).toBeInTheDocument();
  });

  it("does not render Retry button when onRetry is not provided", () => {
    render(<ErrorState message="Some error" />);
    expect(screen.queryByRole("button", { name: /retry/i })).not.toBeInTheDocument();
  });

  it("renders Retry button when onRetry is provided", () => {
    render(<ErrorState message="Some error" onRetry={vi.fn()} />);
    expect(screen.getByRole("button", { name: /retry/i })).toBeInTheDocument();
  });
});

describe("ErrorState — retry interaction", () => {
  it("calls onRetry callback when Retry button is clicked", () => {
    const onRetry = vi.fn();
    render(<ErrorState message="Network error" onRetry={onRetry} />);
    fireEvent.click(screen.getByRole("button", { name: /retry/i }));
    expect(onRetry).toHaveBeenCalledTimes(1);
  });

  it("calls onRetry each time the Retry button is clicked", () => {
    const onRetry = vi.fn();
    render(<ErrorState message="Network error" onRetry={onRetry} />);
    const retryBtn = screen.getByRole("button", { name: /retry/i });
    fireEvent.click(retryBtn);
    fireEvent.click(retryBtn);
    expect(onRetry).toHaveBeenCalledTimes(2);
  });
});
