import { floorNoiseRepository } from "./floorNoiseRepository";
import { projectRepository } from "./projectRepository";
import type { LineRecorderStorage } from "./storage";
import { takeRepository } from "./takeRepository";

export const indexedDbStorage: LineRecorderStorage = {
  projects: projectRepository,
  takes: takeRepository,
  floorNoise: floorNoiseRepository
};
