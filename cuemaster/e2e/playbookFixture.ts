import { readFileSync } from "node:fs";
import JSZip from "jszip";

const manifest = JSON.parse(
  readFileSync(new URL("../tests/fixtures/minimal-playbook/manifest.json", import.meta.url), "utf8")
) as {
  context: Array<{ audio: { path: string } }>;
  roles: Array<{
    lines: Array<{
      cue: { audio: { path: string } };
      response: { segments: Array<{ audio: { path: string } }> };
    }>;
  }>;
};

export async function buildMinimalPlaybookZip(): Promise<Buffer> {
  const zip = new JSZip();
  zip.file("manifest.json", JSON.stringify(manifest));

  for (const audioPath of requiredAudioPaths()) {
    zip.file(audioPath, "");
  }

  return zip.generateAsync({ type: "nodebuffer" });
}

function requiredAudioPaths(): string[] {
  const paths = new Set<string>();
  for (const contextBlock of manifest.context) {
    paths.add(contextBlock.audio.path);
  }
  for (const role of manifest.roles) {
    for (const line of role.lines) {
      paths.add(line.cue.audio.path);
      for (const segment of line.response.segments) {
        paths.add(segment.audio.path);
      }
    }
  }
  return [...paths];
}
