import { ImportRequestButton } from "./components/ImportRequestButton";
import { ProjectDetail } from "./components/ProjectDetail";
import { ProjectInfoPanel } from "./components/ProjectInfoPanel";
import { ProjectLibrary } from "./components/ProjectLibrary";
import { useProjectLibrary } from "./hooks/useProjectLibrary";

export function App() {
  const {
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
  } = useProjectLibrary();

  return (
    <main className="app-shell">
      {selectedProject ? (
        isProjectInfoMode ? (
          <ProjectInfoPanel
            project={selectedProject}
            onBack={hideProjectInfo}
            currentItem={selectedProject.request.items.find((item) => item.id === selectedProject.currentItemId)}
          />
        ) : (
          <ProjectDetail
            project={selectedProject}
            acceptedItemIds={acceptedItemIds}
            status={status}
            onSelectItem={(item) => void selectItem(selectedProject, item)}
            onAccepted={() => loadAcceptedSegments(selectedProject.id)}
            onExport={() => void exportProject(selectedProject)}
            onBack={closeProject}
            onViewInfo={showProjectInfo}
            isExporting={isExporting}
          />
        )
      ) : (
        <>
          <section className="toolbar">
            <div>
              <p className="eyebrow">Quince</p>
              <h1>LineRecorder</h1>
            </div>
            <div className="toolbar-actions">
              <ImportRequestButton isImporting={isImporting} onImport={importRequest} />
            </div>
          </section>

          <p className="status" role="status">
            {status}
          </p>

          <ProjectLibrary
            projects={projects}
            onOpenProject={(project) => void openProject(project)}
            onDeleteProject={(project) => void deleteProject(project)}
          />
        </>
      )}
    </main>
  );
}
