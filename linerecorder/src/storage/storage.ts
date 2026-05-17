import type { FloorNoiseRepository } from "./floorNoiseRepository";
import type { ProjectRepository } from "./projectRepository";
import type { TakeRepository } from "./takeRepository";

export type LineRecorderStorage = {
  projects: ProjectRepository;
  takes: TakeRepository;
  floorNoise: FloorNoiseRepository;
};
