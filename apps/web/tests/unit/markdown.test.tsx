import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { Markdown } from "@/components/ai/markdown";

describe("Markdown (assistant answers)", () => {
  it("renders bold, lists and blockquotes", () => {
    render(<Markdown text={"Your deductible is **$1,000**.\n\n- Collision\n- Comprehensive\n\n> Quoted policy text"} />);
    expect(screen.getByText("$1,000").tagName).toBe("STRONG");
    expect(screen.getAllByRole("listitem")).toHaveLength(2);
    expect(screen.getByText("Quoted policy text").tagName).toBe("BLOCKQUOTE");
  });

  it("never renders raw HTML (XSS-safe)", () => {
    const { container } = render(<Markdown text={'<img src=x onerror="alert(1)"> hi'} />);
    expect(container.querySelector("img")).toBeNull();
    expect(container.textContent).toContain("<img");
  });

  it("turns [n] markers into clickable citations", () => {
    const onCite = vi.fn();
    render(<Markdown text="Covered under collision [1]." onCite={onCite} />);
    fireEvent.click(screen.getByRole("button", { name: "Source 1" }));
    expect(onCite).toHaveBeenCalledWith(1);
  });
});
