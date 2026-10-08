import { describe, expect, it } from "vitest";
import { bytes, money, relativeDays, titleCase } from "@/lib/utils";

describe("formatting utils", () => {
  it("formats money without cents by default", () => {
    expect(money(1916)).toBe("$1,916");
    expect(money(2760.5, { cents: true })).toBe("$2,760.50");
    expect(money(null)).toBe("—");
  });
  it("describes relative days in plain English", () => {
    expect(relativeDays(0)).toBe("today");
    expect(relativeDays(1)).toBe("tomorrow");
    expect(relativeDays(21)).toBe("in 21 days");
    expect(relativeDays(-3)).toBe("3 days ago");
  });
  it("title-cases snake case and formats bytes", () => {
    expect(titleCase("in_review")).toBe("In Review");
    expect(bytes(2048)).toBe("2 KB");
  });
});
