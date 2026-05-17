import { useEffect, useState } from "react";
import type { RecordingItem } from "../../domain/recordingItem";
import type { RecordingTake } from "../../domain/take";
import { exportRoleRecordings, RoleRecordingsExportError } from "../../package/exportRoleRecordings";
import { importRecordingRequest, RecordingRequestImportError } from "../../package/importRecordingRequest";
import { browserDownloadService } from "../../platform/download";
import type { RecordingProjectRecord } from "../../storage/db";
import { indexedDbStorage } from "../../storage/indexedDbStorage";
import type { LineRecorderStorage } from "../../storage/storage";

type DownloadService = {
  download(download: { blob: Blob; fileName: string }): void;
};

type UseProjectLibraryDependencies = {
  storage: LineRecorderStorage;
  downloadService: DownloadService;
  importRequest: typeof importRecordingRequest;
  exportRecordings: typeof exportRoleRecordings;
  confirmDelete: (message: string) => boolean;
};

const defaultDependencies: UseProjectLibraryDependencies = {
  storage: indexedDbStorage,
  downloadService: browserDownloadService,
  importRequest: importRecordingRequest,
  exportRecordings: exportRoleRecordings,
  confirmDelete: (message) => window.confirm(message)
};

export function useProjectLibrary(dependencies: UseProjectLibraryDependencies = defaultDependencies) {
  const [projects, setProjects] = useState<RecordingProjectRecord[]>([]);
  const [selectedProject, setSelectedProject] = useState<RecordingProjectRecord | null>(null);
  const [isProjectInfoMode, setIsProjectInfoMode] = useState(false);
  const [acceptedItemIds, setAcceptedItemIds] = useState<Set<string>>(new Set());
  const [status, setStatus] = useState("Import a Stager Recording Request to begin.");
  const [isImporting, setIsImporting] = useState(false);
  const [isExporting, setIsExporting] = useState(false);

  useEffect(() => {
    void loadProjects();
  }, []);

  async function loadProjects(): Promise<void> {
    setProjects(await dependencies.storage.projects.list());
  }

  async function openProject(project: RecordingProjectRecord): Promise<void> {
    setSelectedProject(project);
    setIsProjectInfoMode(false);
    setStatus(`Opened ${project.request.role.displayName}.`);
    await loadAcceptedSegments(project.id);
  }

  async function loadAcceptedSegments(projectId: string): Promise<void> {
    const acceptedTakes = await dependencies.storage.takes.acceptedForProject(projectId);
    setAcceptedItemIds(new Set(acceptedTakes.map((take: RecordingTake) => take.segmentId)));
  }

  async function selectItem(project: RecordingProjectRecord, item: RecordingItem): Promise<void> {
    await dependencies.storage.projects.setCurrentItem(project.id, item.id);
    const updatedProject = {
      ...project,
      currentItemId: item.id
    };
    setSelectedProject(updatedProject);
    setProjects((currentProjects) =>
      currentProjects.map((candidate) => (candidate.id === updatedProject.id ? updatedProject : candidate))
    );
    setStatus(`Selected ${item.id}.`);
  }

  async function importRequest(file: File): Promise<void> {
    setIsImporting(true);
    setStatus("Importing Recording Request...");
    try {
      const request = await dependencies.importRequest(file);
      const project = await dependencies.storage.projects.saveImportedRequest(request);
      await loadProjects();
      await openProject(project);
      setStatus(`Imported ${request.items.length} lines for ${project.request.role.displayName}.`);
    } catch (error) {
      const message =
        error instanceof RecordingRequestImportError ? error.message : "Unable to import Recording Request.";
      setStatus(message);
    } finally {
      setIsImporting(false);
    }
  }

  async function exportProject(project: RecordingProjectRecord): Promise<void> {
    setIsExporting(true);
    setStatus("Exporting role recordings...");
    try {
      const acceptedTakes = await dependencies.storage.takes.acceptedForProject(project.id);
      const floorNoiseRecordings = await dependencies.storage.floorNoise.forProject(project.id);
      const exported = await dependencies.exportRecordings(project, acceptedTakes, floorNoiseRecordings);
      dependencies.downloadService.download({ blob: exported.blob, fileName: exported.fileName });
      const exportedCount = exported.manifest.recordings.length;
      const missingCount = exported.manifest.missing_segment_ids.length;
      setStatus(
        exported.manifest.complete
          ? `Exported ${exported.fileName} with ${exportedCount} recordings. Send this zip to the showrunner.`
          : `Exported partial package ${exported.fileName} with ${exportedCount} recordings; ${missingCount} still missing. Send this zip to the showrunner.`
      );
    } catch (error) {
      setStatus(error instanceof RoleRecordingsExportError ? error.message : "Unable to export role recordings.");
    } finally {
      setIsExporting(false);
    }
  }

  async function deleteProject(project: RecordingProjectRecord): Promise<void> {
    const confirmed = dependencies.confirmDelete(
      `Delete ${project.request.role.displayName} for ${project.request.play.title}? This removes the local request and all saved takes from this browser.`
    );
    if (!confirmed) {
      return;
    }

    await dependencies.storage.projects.delete(project.id);
    if (selectedProject?.id === project.id) {
      setSelectedProject(null);
      setIsProjectInfoMode(false);
    }
    await loadProjects();
    setStatus(`Deleted local recordings for ${project.request.role.displayName}.`);
  }

  function showProjectInfo(item?: RecordingItem): void {
    setSelectedProject((current) =>
      current === null ? current : { ...current, currentItemId: item?.id ?? current.currentItemId }
    );
    setIsProjectInfoMode(true);
  }

  function hideProjectInfo(): void {
    setIsProjectInfoMode(false);
  }

  function closeProject(): void {
    setSelectedProject(null);
  }

  return {
    projects,
    selectedProject,
    isProjectInfoMode,
    acceptedItemIds,
    status,
    isImporting,
    isExporting,
    openProject,
    closeProject,
    selectItem,
    importRequest,
    exportProject,
    deleteProject,
    loadAcceptedSegments,
    showProjectInfo,
    hideProjectInfo
  };
}
