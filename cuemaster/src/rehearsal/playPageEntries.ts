import type { Line } from "../domain/line";
import type { Playbook } from "../domain/playbook";

export type PlayPageEntry =
  | {
      type: "line";
      id: string;
      blockId: string;
      partId: number | null;
      speaker: string;
      text: string;
      line: Line;
      inlineDirectionAudioPaths: Array<{
        segmentId: string;
        path: string;
      }>;
      sourceOrder: number;
    }
  | {
      type: "context";
      id: string;
      blockId: string;
      partId: number | null;
      speaker: string;
      text: string;
      audioPath: string;
      sourceOrder: number;
    };

export type DirectionAudioLookup = {
  resolvePath(line: Line, segmentId: string): string | null;
};

const includedContextKinds = new Set(["heading", "description", "direction"]);

export function buildPlayEntries(playbook: Playbook, includeNarration: boolean, directionAudioLookup: DirectionAudioLookup): PlayPageEntry[] {
  const linesById = new Map<string, Line>();
  const contextEntries: PlayPageEntry[] = [];
  let sourceOrder = 0;

  for (const role of playbook.roles) {
    for (const line of role.lines) {
      const prior = linesById.get(line.id);
      if (!prior || blockOrderForLine(line) < blockOrderForLine(prior)) {
        linesById.set(line.id, line);
      }
    }
  }

  if (includeNarration) {
    for (const block of playbook.context) {
      if (!block.audioPath || !includedContextKinds.has(block.kind)) {
        continue;
      }
      contextEntries.push({
        type: "context",
        id: block.id,
        blockId: block.blockId,
        partId: block.partId,
        speaker: block.speaker,
        text: block.text,
        audioPath: block.audioPath,
        sourceOrder
      });
      sourceOrder += 1;
    }
  }

  const lines: Array<Extract<PlayPageEntry, { type: "line" }>> = Array.from(linesById.values())
    .sort((left, right) => blockOrderForBlockId(left.blockId) - blockOrderForBlockId(right.blockId))
    .map((line) => {
      const inlineDirectionAudioPaths: Array<{ segmentId: string; path: string }> = [];
      if (includeNarration) {
        for (const direction of line.directions) {
          if (direction.placement !== "inline") {
            continue;
          }
          const directionPath = directionAudioLookup.resolvePath(line, direction.segmentId);
          if (directionPath !== null) {
            inlineDirectionAudioPaths.push({
              segmentId: direction.segmentId,
              path: directionPath
            });
          }
        }
      }

      return {
        type: "line",
        id: line.id,
        blockId: line.blockId,
        partId: line.partId,
        speaker: line.speaker,
        text: line.responseText,
        line,
        inlineDirectionAudioPaths,
        sourceOrder: sourceOrder++
      };
    });

  return [...lines, ...contextEntries]
    .sort((left, right) => {
      const leftOrder = blockOrderForBlockId(left.blockId);
      const rightOrder = blockOrderForBlockId(right.blockId);
      if (leftOrder !== rightOrder) {
        return leftOrder - rightOrder;
      }
      if (left.type !== right.type) {
        return left.type === "context" ? -1 : 1;
      }
      return left.sourceOrder - right.sourceOrder;
    });
}

export function buildDirectionAudioPathLookup(playbook: Playbook): DirectionAudioLookup {
  const segmentMap = new Map<string, string>();
  const ambiguousSegments = new Set<string>();
  const candidateSegmentsByRole = new Map<string, string[]>();

  const addPath = (rawPath: string) => {
    const normalizedPath = normalizeAssetPath(rawPath);
    const match = normalizedPath.match(/^audio\/segments\/([^/]+)\/(.+)\.[a-zA-Z0-9]+$/);
    if (!match) {
      return;
    }
    const [, role, segmentId] = match;
    const roleKey = normalizeRoleForPath(role);
    const key = `${roleKey}:${segmentId}`;
    const existing = segmentMap.get(key);
    if (existing === undefined) {
      segmentMap.set(key, normalizedPath);
      candidateSegmentsByRole.set(segmentId, [...(candidateSegmentsByRole.get(segmentId) ?? []), normalizedPath]);
      return;
    }
    if (existing !== normalizedPath) {
      ambiguousSegments.add(key);
    }
  };

  if (playbook.audioAssetPaths) {
    for (const path of playbook.audioAssetPaths) {
      addPath(path);
    }
  }

  for (const role of playbook.roles) {
    for (const line of role.lines) {
      addPath(line.cue.audioPath);
      for (const segment of line.responseSegments) {
        addPath(segment.audioPath);
      }
    }
  }

  for (const block of playbook.context) {
    if (block.audioPath) {
      addPath(block.audioPath);
    }
  }

  return {
    resolvePath(line: Line, segmentId: string) {
      const preferredRoles = [
        normalizeRoleForPath(line.speaker),
        normalizeRoleForPath(line.cue.speaker),
        "NARRATOR"
      ];

      for (const role of preferredRoles) {
        const key = `${role}:${segmentId}`;
        if (ambiguousSegments.has(key)) {
          continue;
        }
        const candidate = segmentMap.get(key);
        if (candidate) {
          return candidate;
        }
      }

      const ambiguousCandidates = candidateSegmentsByRole.get(segmentId);
      if (!ambiguousCandidates || ambiguousCandidates.length === 0) {
        return null;
      }
      if (ambiguousCandidates.length === 1) {
        return ambiguousCandidates[0];
      }
      for (const role of preferredRoles) {
        const key = `${role}:${segmentId}`;
        const candidate = segmentMap.get(key);
        if (candidate && !ambiguousSegments.has(key)) {
          return candidate;
        }
      }
      return null;
    }
  };
}

export function compareSegmentIds(left: string, right: string): number {
  if (left === right) {
    return 0;
  }
  const leftParts = splitSegmentId(left);
  const rightParts = splitSegmentId(right);
  const sharedLength = Math.min(leftParts.length, rightParts.length);
  for (let index = 0; index < sharedLength; index += 1) {
    const leftPart = leftParts[index];
    const rightPart = rightParts[index];
    if (leftPart === rightPart) {
      continue;
    }
    const leftIsNumber = typeof leftPart === "number";
    const rightIsNumber = typeof rightPart === "number";
    if (leftIsNumber && rightIsNumber) {
      return leftPart - rightPart;
    }
    if (leftIsNumber !== rightIsNumber) {
      return leftIsNumber ? -1 : 1;
    }
    return String(leftPart).localeCompare(String(rightPart));
  }
  return leftParts.length - rightParts.length;
}

function normalizeAssetPath(assetPath: string): string {
  return assetPath.replace(/^\/+/, "");
}

function normalizeRoleForPath(role: string): string {
  return role.trim().toUpperCase().replace(/^_+/, "");
}

function splitSegmentId(segmentId: string): Array<string | number> {
  const tokens = segmentId.split(/[^\da-zA-Z]+/).filter((token) => token.length > 0);
  return tokens.map((token) => {
    const value = Number(token);
    return Number.isFinite(value) && String(value) === token ? value : token;
  });
}

function blockOrderForBlockId(blockId: string): number {
  return blockId
    .split(".")
    .reduce((total, part, index) => total + Number(part) * 1000 ** (3 - index), 0);
}

function blockOrderForLine(line: Line): number {
  return blockOrderForBlockId(line.blockId);
}
