import { describe, expect, it } from "vitest";
import manifestFixture from "../fixtures/minimal-playbook/manifest.json";
import { normalizePlaybook } from "../../src/playbook/normalizePlaybook";
import { RehearsalEngine } from "../../src/rehearsal/rehearsalEngine";
import { validatePlaybookManifest } from "../../src/specs/validatePlaybookManifest";

const playbook = normalizePlaybook(validatePlaybookManifest(manifestFixture));

describe("RehearsalEngine", () => {
  it("selects an actor role and starts at the first line", () => {
    const engine = RehearsalEngine.forRole(playbook, "ANDROCLES");

    expect(engine.selectedRole().id).toBe("ANDROCLES");
    expect(engine.currentLine()?.id).toBe("I-1");
    expect(engine.position()).toEqual({ index: 0, total: 2, atBeginning: true, atEnd: false });
  });

  it("can start from a chosen line", () => {
    const engine = RehearsalEngine.forRole(playbook, "ANDROCLES", { startLineId: "I-3" });

    expect(engine.currentLine()?.id).toBe("I-3");
    expect(engine.position().atEnd).toBe(true);
  });

  it("walks forward and backward through a selected role", () => {
    const engine = RehearsalEngine.forRole(playbook, "ANDROCLES");

    expect(engine.next()?.id).toBe("I-3");
    expect(engine.next()?.id).toBe("I-3");
    expect(engine.previous()?.id).toBe("I-1");
    expect(engine.previous()?.id).toBe("I-1");
  });

  it("updates cue payloads immediately after navigation", () => {
    const engine = RehearsalEngine.forRole(playbook, "ANDROCLES");

    expect(engine.cuePayloads().map((cue) => cue.text)).toEqual(["PROLOGUE"]);
    engine.next();
    expect(engine.cuePayloads().map((cue) => cue.text)).toEqual(["You are always talking nonsense."]);
    engine.previous();
    expect(engine.cuePayloads().map((cue) => cue.text)).toEqual(["PROLOGUE"]);
  });

  it("plays only the immediate cue for the full cue preset", () => {
    const engine = RehearsalEngine.forRole(playbook, "ANDROCLES", { startLineId: "I-3" });

    expect(engine.cuePayloads("full").map((cue) => cue.text)).toEqual(["You are always talking nonsense."]);
  });

  it("plays no cue for the no-cue preset", () => {
    const engine = RehearsalEngine.forRole(playbook, "ANDROCLES", { startLineId: "I-3" });

    expect(engine.cuePayloads("none")).toEqual([]);
  });

  it("uses enough preceding cues to satisfy a timed cue-length preset", () => {
    const engine = RehearsalEngine.forRole(playbook, "ANDROCLES", { startLineId: "I-3" });

    expect(engine.cuePayloads("last_5s").map((cue) => cue.text)).toEqual([
      "PROLOGUE",
      "You are always talking nonsense."
    ]);
  });

  it("preserves line-specific target hesitation timing", () => {
    const engine = RehearsalEngine.forRole(playbook, "ANDROCLES");

    expect(engine.currentLine()?.timing?.targetHesitationMs).toBe(750);
    expect(engine.next()?.timing).toBeUndefined();
  });

  it("tracks whether stage directions should be included", () => {
    const engine = RehearsalEngine.forRole(playbook, "ANDROCLES", { includeDirections: false });

    expect(engine.includeDirections()).toBe(false);
    engine.setIncludeDirections(true);
    expect(engine.includeDirections()).toBe(true);
  });

  it("raises for unknown roles and start lines", () => {
    expect(() => RehearsalEngine.forRole(playbook, "_NARRATOR")).toThrow("Role not found: _NARRATOR");
    expect(() => RehearsalEngine.forRole(playbook, "ANDROCLES", { startLineId: "missing" })).toThrow(
      "Line not found for role ANDROCLES: missing"
    );
  });
});
