import { describe, expect, it, vi } from "vitest";
import { BrowserDownloadService } from "../../src/platform/download";

describe("BrowserDownloadService", () => {
  it("downloads a blob with the requested filename and releases the object URL", () => {
    Object.defineProperty(URL, "createObjectURL", {
      configurable: true,
      value: () => "blob:initial"
    });
    Object.defineProperty(URL, "revokeObjectURL", {
      configurable: true,
      value: () => undefined
    });
    const createObjectURL = vi.spyOn(URL, "createObjectURL").mockReturnValue("blob:role-recordings");
    const revokeObjectURL = vi.spyOn(URL, "revokeObjectURL").mockImplementation(() => undefined);
    const click = vi.spyOn(HTMLAnchorElement.prototype, "click").mockImplementation(() => undefined);

    new BrowserDownloadService().download({
      blob: new Blob(["zip"], { type: "application/zip" }),
      fileName: "androcles-CENTURION-role-recordings-20260510T140000Z.zip"
    });

    expect(createObjectURL).toHaveBeenCalledOnce();
    expect(click).toHaveBeenCalledOnce();
    expect(revokeObjectURL).toHaveBeenCalledWith("blob:role-recordings");
    expect(document.querySelector("a[download]")).toBeNull();

    createObjectURL.mockRestore();
    revokeObjectURL.mockRestore();
    click.mockRestore();
  });
});
