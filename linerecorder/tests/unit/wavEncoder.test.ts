import { describe, expect, it } from "vitest";
import { encodeWav } from "../../src/audio/wavEncoder";

describe("encodeWav", () => {
  it("writes a mono PCM WAV blob", async () => {
    const blob = encodeWav({
      samples: [new Float32Array([-1, 0, 1])],
      sampleRateHz: 48000,
      channels: 1
    });
    const view = new DataView(await blobArrayBuffer(blob));

    expect(blob.type).toBe("audio/wav");
    expect(ascii(view, 0, 4)).toBe("RIFF");
    expect(ascii(view, 8, 4)).toBe("WAVE");
    expect(ascii(view, 12, 4)).toBe("fmt ");
    expect(view.getUint16(22, true)).toBe(1);
    expect(view.getUint32(24, true)).toBe(48000);
    expect(ascii(view, 36, 4)).toBe("data");
    expect(view.getUint32(40, true)).toBe(6);
  });

  it("rejects non-mono input", () => {
    expect(() =>
      encodeWav({
        samples: [new Float32Array([0])],
        sampleRateHz: 48000,
        channels: 2
      })
    ).toThrow("Only mono WAV encoding is supported.");
  });
});

function ascii(view: DataView, offset: number, length: number): string {
  return Array.from({ length }, (_, index) => String.fromCharCode(view.getUint8(offset + index))).join("");
}

function blobArrayBuffer(blob: Blob): Promise<ArrayBuffer> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(reader.result as ArrayBuffer);
    reader.onerror = () => reject(reader.error);
    reader.readAsArrayBuffer(blob);
  });
}
