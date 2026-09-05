import { describe, expect, it } from "vitest";
import { decisionTone, formatMoney } from "./format";

describe("format helpers", () => {
  it("formats paise as INR", () => expect(formatMoney(875000)).toContain("8,750"));
  it("maps decisions to semantic tones", () => {
    expect(decisionTone("ALLOW")).toBe("safe");
    expect(decisionTone("VERIFY")).toBe("warn");
    expect(decisionTone("BLOCK")).toBe("danger");
  });
});
