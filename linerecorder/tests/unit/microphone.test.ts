import { describe, expect, it, vi } from "vitest";
import { MicrophoneSession } from "../../src/audio/microphoneSession";
import { createMicrophoneConstraints } from "../../src/platform/microphone";

describe("createMicrophoneConstraints", () => {
  it("uses clean-room constraints by default", () => {
    expect(createMicrophoneConstraints(undefined, "clean")).toEqual({
      deviceId: undefined,
      channelCount: 1,
      echoCancellation: false,
      noiseSuppression: false,
      autoGainControl: false
    });
  });

  it("uses exact selected input and browser processing in noisy mode", () => {
    expect(createMicrophoneConstraints("mic-1", "noisy")).toEqual({
      deviceId: { exact: "mic-1" },
      channelCount: 1,
      echoCancellation: true,
      noiseSuppression: true,
      autoGainControl: true
    });
  });
});

describe("MicrophoneSession", () => {
  it("reports input readings and cleans up resources", async () => {
    const stream = fakeStream();
    const stopStream = vi.fn();
    const close = vi.fn();
    const cancelFrame = vi.fn();
    const readings: Array<{ energy: number; level: string }> = [];
    const session = new MicrophoneSession((reading) => readings.push(reading), {
      requestStream: vi.fn(async () => stream as unknown as MediaStream),
      stopStream,
      createAudioContext: () => fakeAudioContext(close) as unknown as AudioContext,
      requestFrame: vi.fn(() => 42),
      cancelFrame
    });

    await session.start(undefined, "clean");
    session.stop();

    expect(readings).toHaveLength(1);
    expect(readings[0].level).toBe("good");
    expect(stopStream).toHaveBeenCalledWith(stream);
    expect(cancelFrame).toHaveBeenCalledWith(42);
    expect(close).toHaveBeenCalled();
  });
});

function fakeStream() {
  return {
    getTracks: () => []
  };
}

function fakeAudioContext(close: () => void) {
  return {
    createMediaStreamSource: () => ({
      connect: vi.fn()
    }),
    createAnalyser: () => ({
      fftSize: 1024,
      getByteTimeDomainData: (samples: Uint8Array) => {
        samples.fill(160);
      }
    }),
    close
  };
}
