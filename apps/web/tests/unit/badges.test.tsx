import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { CertaintyTag, ConfidenceBadge, SeverityBadge } from "@/components/ui/primitives";

// Meaning must never rely on color alone: every state carries a text label.
describe("status badges", () => {
  it.each([
    ["high", "High confidence"],
    ["moderate", "Moderate confidence"],
    ["needs_verification", "Needs verification"],
    ["human_review", "Human review recommended"],
  ] as const)("confidence %s has a text label", (c, label) => {
    render(<ConfidenceBadge confidence={c} />);
    expect(screen.getByText(label)).toBeInTheDocument();
  });

  it("labels certainty and severity in words", () => {
    render(<><CertaintyTag certainty="possible" /><SeverityBadge severity="attention" /></>);
    expect(screen.getByText("Possible")).toBeInTheDocument();
    expect(screen.getByText("Needs attention")).toBeInTheDocument();
  });
});
