import { describe, expect, it } from "vitest";
import { sanitizeSvgIconLibrary } from "../../src/staging/svgIconLibrary";

describe("sanitizeSvgIconLibrary", () => {
  it("keeps valid stage icon symbols", () => {
    const sanitized = sanitizeSvgIconLibrary(
      '<defs><symbol id="stage-icon-table" viewBox="0 0 24 24"><path d="M4 8h16"/></symbol></defs>'
    );

    expect(sanitized).toContain('id="stage-icon-table"');
    expect(sanitized).toContain('d="M4 8h16"');
  });

  it("removes unsupported elements and event attributes", () => {
    const sanitized = sanitizeSvgIconLibrary(
      '<defs><script>alert(1)</script><symbol id="stage-icon-table" viewBox="0 0 24 24" onload="alert(1)"><path d="M4 8h16" onclick="alert(1)"/></symbol></defs>'
    );

    expect(sanitized).not.toContain("script");
    expect(sanitized).not.toContain("onload");
    expect(sanitized).not.toContain("onclick");
    expect(sanitized).toContain('id="stage-icon-table"');
  });
});
