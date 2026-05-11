import { describe, expect, it } from "vitest";
import { formatBytes } from "../../src/platform/storageEstimate";

describe("formatBytes", () => {
  it("formats unknown storage values", () => {
    expect(formatBytes(null)).toBe("unknown");
  });

  it("formats byte counts for storage diagnostics", () => {
    expect(formatBytes(512)).toBe("512 B");
    expect(formatBytes(1024 * 1024)).toBe("1.0 MB");
    expect(formatBytes(322 * 1024 * 1024)).toBe("322 MB");
    expect(formatBytes(3 * 1024 * 1024 * 1024)).toBe("3.0 GB");
  });
});
