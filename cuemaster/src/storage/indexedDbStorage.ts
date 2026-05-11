import { audioAssetRepository } from "./audioAssetRepository";
import { bookmarkRepository } from "./bookmarkRepository";
import { playbookRepository } from "./playbookRepository";
import { sessionRepository } from "./sessionRepository";
import { timingAttemptRepository } from "./timingAttemptRepository";
import type { CuemasterStorage } from "./storage";

export const indexedDbStorage: CuemasterStorage = {
  playbooks: playbookRepository,
  sessions: sessionRepository,
  audioAssets: audioAssetRepository,
  bookmarks: bookmarkRepository,
  timingAttempts: timingAttemptRepository
};
