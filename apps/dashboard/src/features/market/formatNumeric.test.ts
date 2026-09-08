import { formatPrice, formatStrike } from "./formatNumeric";

describe("formatPrice", () => {
  it("renders the storage scale as a two-decimal money value", () => {
    expect(formatPrice("180.2500000000")).toBe("180.25");
  });

  it("groups thousands and pads a short fraction", () => {
    expect(formatPrice("1234.5")).toBe("1,234.50");
  });

  it("accepts a number as well as decimal text", () => {
    expect(formatPrice(180.25)).toBe("180.25");
  });

  it("keeps unparseable text visible rather than inferring a value", () => {
    expect(formatPrice("")).toBe("");
    expect(formatPrice("n/a")).toBe("n/a");
  });
});

describe("formatStrike", () => {
  it("removes the trailing zeros the storage scale adds", () => {
    expect(formatStrike("175.0000000000")).toBe("175");
  });

  it("keeps a significant fractional strike", () => {
    expect(formatStrike("177.5000000000")).toBe("177.5");
  });

  it("keeps unparseable text visible rather than inferring a value", () => {
    expect(formatStrike("")).toBe("");
  });
});
