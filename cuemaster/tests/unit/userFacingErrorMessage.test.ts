import { describe, expect, it } from "vitest";
import { MicrophonePermissionError } from "../../src/platform/microphone";
import { PlaybookImportError } from "../../src/playbook/playbookImportError";
import { userFacingErrorMessage } from "../../src/ui/errors/userFacingErrorMessage";

describe("userFacingErrorMessage", () => {
  it("preserves strict Playbook import errors", () => {
    expect(userFacingErrorMessage(new PlaybookImportError("Playbook zip is missing manifest.json"))).toBe(
      "Playbook zip is missing manifest.json"
    );
  });

  it("reports storage quota failures clearly", () => {
    expect(userFacingErrorMessage(new DOMException("full", "QuotaExceededError"))).toBe(
      "Local storage is full. Remove an imported Playbook or free browser storage, then try again."
    );
  });

  it("reports IndexedDB failures clearly", () => {
    expect(userFacingErrorMessage(new DOMException("bad record", "DataError"))).toBe(
      "Local browser storage could not be read. Try refreshing; if the problem persists, clear Cuemaster site data and re-import Playbooks."
    );
  });

  it("reports browser autoplay failures clearly", () => {
    expect(userFacingErrorMessage(new DOMException("blocked", "NotAllowedError"))).toBe(
      "The browser blocked playback. Press a playback button again to start audio."
    );
  });

  it("reports unsupported or failed audio playback clearly", () => {
    expect(userFacingErrorMessage(new Error("Audio playback failed: blob://asset"))).toBe(
      "Audio playback failed. This browser may not support the Playbook audio format."
    );
  });

  it("preserves microphone permission errors", () => {
    expect(userFacingErrorMessage(new MicrophonePermissionError("No browser microphone API is available."))).toBe(
      "No browser microphone API is available."
    );
  });
});
