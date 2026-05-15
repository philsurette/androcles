import type { Line } from "../domain/line";
import type { Playbook } from "../domain/playbook";

export type LineCallout = {
  speaker: string;
  audioPath: string;
};

export function buildCalloutResolver(playbook: Playbook) {
  const lookup = buildCalloutAudioResolver(playbook.audioAssetPaths ?? []);

  return (line: Line | null): LineCallout | null => {
    if (!line) {
      return null;
    }
    const candidates = [line.speaker, line.role];
    let audioPath: string | undefined;
    for (const candidate of candidates) {
      audioPath = lookup.get(normalizeSpeaker(candidate));
      if (audioPath) {
        break;
      }
    }
    if (!audioPath) {
      return null;
    }
    return {
      speaker: line.speaker,
      audioPath
    };
  };
}

export function buildCalloutResolverForSpeaker(playbook: Playbook) {
  const lookup = buildCalloutAudioResolver(playbook.audioAssetPaths ?? []);
  return (speaker: string | null): LineCallout | null => {
    if (!speaker) {
      return null;
    }
    const audioPath = lookup.get(normalizeSpeaker(speaker));
    if (!audioPath) {
      return null;
    }
    return {
      speaker,
      audioPath
    };
  };
}

function buildCalloutAudioResolver(audioAssetPaths: string[]): Map<string, string> {
  const index = new Map<string, string>();
  for (const rawPath of audioAssetPaths) {
    const path = normalizeAssetPath(rawPath);
    const match = path.match(/^audio\/callouts\/([^/]+)\/([^/]+)\.[^./]+$/);
    if (!match) {
      const legacyMatch = path.match(/^audio\/callouts\/([^./]+)\.[^./]+$/);
      if (legacyMatch) {
        index.set(normalizeSpeaker(legacyMatch[1]), path);
      }
      continue;
    }
    const folderSpeaker = normalizeSpeaker(match[1]);
    const fileSpeaker = normalizeSpeaker(match[2]);
    if (folderSpeaker !== fileSpeaker) {
      continue;
    }
    if (!index.has(folderSpeaker)) {
      index.set(folderSpeaker, path);
    }
  }
  return index;
}

function normalizeSpeaker(speaker: string): string {
  return speaker.trim().replace(/^_+/, "").toUpperCase();
}

function normalizeAssetPath(assetPath: string): string {
  return assetPath.replace(/^\/+/, "").replace(/\\/g, "/");
}
