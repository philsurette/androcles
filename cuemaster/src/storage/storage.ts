import type { Bookmark } from "../domain/bookmark";
import type { Playbook } from "../domain/playbook";
import type { RehearsalSession } from "../domain/session";
import type { TimingAttempt } from "../domain/timingAttempt";
import type { StoredAudioAsset } from "./audioAssetRepository";
import type { StoredJsonAsset } from "./jsonAssetRepository";

export type PlaybookRepository = {
  list(): Promise<Playbook[]>;
  get(id: string): Promise<Playbook | undefined>;
  save(playbook: Playbook): Promise<unknown>;
  delete(id: string): Promise<unknown>;
};

export type SessionRepository = {
  get(playbookId: string, roleId: string): Promise<RehearsalSession | undefined>;
  getLatestForPlaybook(playbookId: string): Promise<RehearsalSession | undefined>;
  save(session: RehearsalSession): Promise<unknown>;
  deleteForPlaybook(playbookId: string): Promise<unknown>;
};

export type AudioAssetRepository = {
  save(asset: StoredAudioAsset): Promise<unknown>;
  get(playbookId: string, path: string): Promise<StoredAudioAsset | undefined>;
  deleteForPlaybook(playbookId: string): Promise<unknown>;
};

export type JsonAssetRepository = {
  save(asset: StoredJsonAsset): Promise<unknown>;
  get(playbookId: string, path: string): Promise<StoredJsonAsset | undefined>;
  deleteForPlaybook(playbookId: string): Promise<unknown>;
};

export type BookmarkRepository = {
  get(playbookId: string, roleId: string, lineId: string): Promise<Bookmark | undefined>;
  listForRole(playbookId: string, roleId: string): Promise<Bookmark[]>;
  save(bookmark: Bookmark): Promise<unknown>;
  delete(playbookId: string, roleId: string, lineId: string): Promise<unknown>;
  deleteForPlaybook(playbookId: string): Promise<unknown>;
};

export type TimingAttemptRepository = {
  save(attempt: TimingAttempt): Promise<void>;
  latestForLine(playbookId: string, roleId: string, lineId: string): Promise<TimingAttempt | undefined>;
  recentForLine(playbookId: string, roleId: string, lineId: string, limit?: number): Promise<TimingAttempt[]>;
  latestForRole(playbookId: string, roleId: string): Promise<TimingAttempt[]>;
  deleteForPlaybook(playbookId: string): Promise<unknown>;
};

export type CuemasterStorage = {
  playbooks: PlaybookRepository;
  sessions: SessionRepository;
  audioAssets: AudioAssetRepository;
  jsonAssets: JsonAssetRepository;
  bookmarks: BookmarkRepository;
  timingAttempts: TimingAttemptRepository;
};
