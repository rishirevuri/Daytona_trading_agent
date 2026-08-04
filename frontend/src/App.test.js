import { changeTone, number, signedPercent } from "./App";

test("formats provider values without inventing missing numbers", () => {
  expect(number(1234.567, 1)).toBe("1,234.6");
  expect(number(null)).toBe("--");
  expect(signedPercent(-0.25)).toBe("-0.25%");
  expect(signedPercent(undefined)).toBe("--");
});

test("does not classify unavailable changes as losses", () => {
  expect(changeTone(null)).toBe("neutral");
  expect(changeTone("not-a-number")).toBe("neutral");
  expect(changeTone(-0.25)).toBe("negative");
  expect(changeTone(0)).toBe("positive");
});
