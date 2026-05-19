import { audioAssetRepository } from "./audioAssetRepository";
import { bookmarkRepository } from "./bookmarkRepository";
import { jsonAssetRepository } from "./jsonAssetRepository";
import { playbookRepository } from "./playbookRepository";
import { sessionRepository } from "./sessionRepository";
import { timingAttemptRepository } from "./timingAttemptRepository";
import type { CuemasterStorage } from "./storage";

export const indexedDbStorage: CuemasterStorage = {
  playbooks: playbookRepository,
  sessions: sessionRepository,
  audioAssets: audioAssetRepository,
  jsonAssets: jsonAssetRepository,
  bookmarks: bookmarkRepository,
  timingAttempts: timingAttemptRepository
};
