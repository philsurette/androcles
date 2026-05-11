import { useState } from "react";
import type { Playbook } from "../domain/playbook";
import type { Role } from "../domain/role";
import type { RehearsalSession } from "../domain/session";
import { defaultTargetHesitationMs } from "../rehearsal/tempoTimingConfig";
import { indexedDbStorage } from "../storage/indexedDbStorage";
import { LibraryScreen } from "../ui/screens/LibraryScreen";
import { RehearsalScreen } from "../ui/screens/RehearsalScreen";
import { RoleSelectScreen } from "../ui/screens/RoleSelectScreen";
import { userFacingErrorMessage } from "../ui/errors/userFacingErrorMessage";

export function App() {
  const [selectedPlaybook, setSelectedPlaybook] = useState<Playbook | null>(null);
  const [selectedRole, setSelectedRole] = useState<Role | null>(null);
  const [selectedSession, setSelectedSession] = useState<RehearsalSession | null>(null);
  const [storageStatus, setStorageStatus] = useState<string>("");

  if (selectedPlaybook && selectedRole) {
    return (
      <RehearsalScreen
        playbook={selectedPlaybook}
        role={selectedRole}
        initialSession={selectedSession}
        initialStorageStatus={storageStatus}
        onBack={() => {
          setSelectedRole(null);
          setSelectedSession(null);
        }}
      />
    );
  }

  if (selectedPlaybook) {
    return (
      <RoleSelectScreen
        playbook={selectedPlaybook}
        storageStatus={storageStatus}
        onBack={() => setSelectedPlaybook(null)}
        onSelectRole={(role, startLineId) => void selectRole(selectedPlaybook, role, startLineId)}
      />
    );
  }

  return (
    <LibraryScreen
      onSelectPlaybook={(playbook) => void openPlaybook(playbook)}
    />
  );

  async function openPlaybook(playbook: Playbook) {
    let latestSession: RehearsalSession | undefined;
    setStorageStatus("");
    try {
      latestSession = await indexedDbStorage.sessions.getLatestForPlaybook(playbook.id);
    } catch (error) {
      latestSession = undefined;
      setStorageStatus(userFacingErrorMessage(error));
    }
    const latestRole = latestSession
      ? playbook.roles.find((candidate) => candidate.id === latestSession.roleId)
      : undefined;

    setSelectedPlaybook(playbook);
    setSelectedRole(latestRole ?? null);
    setSelectedSession(latestRole ? (latestSession ?? null) : null);
  }

  async function selectRole(playbook: Playbook, role: Role, startLineId?: string) {
    setStorageStatus("");
    try {
      const savedSession = (await indexedDbStorage.sessions.get(playbook.id, role.id)) ?? null;
      if (!startLineId) {
        setSelectedRole(role);
        setSelectedSession(savedSession);
        return;
      }
      const lineIndex = role.lines.findIndex((line) => line.id === startLineId);
      if (lineIndex < 0) {
        throw new Error(`Line not found for role ${role.id}: ${startLineId}`);
      }
      const nextSession = {
        playbookId: playbook.id,
        roleId: role.id,
        lineIndex,
        cueDepth: savedSession?.cueDepth ?? 1,
        includeDirections: savedSession?.includeDirections ?? true,
        revealLine: savedSession?.showLinesByDefault ?? savedSession?.revealLine ?? false,
        showLinesByDefault: savedSession?.showLinesByDefault ?? savedSession?.revealLine ?? false,
        cueWindowPresetId: savedSession?.cueWindowPresetId ?? "full",
        playbackRate: savedSession?.playbackRate ?? 1,
        speakAlongEnabled: savedSession?.speakAlongEnabled ?? false,
        speakAlongPauseMs: savedSession?.speakAlongPauseMs ?? defaultTargetHesitationMs,
        tempoTargetHesitationMs:
          savedSession?.tempoTargetHesitationMs ?? savedSession?.speakAlongPauseMs ?? defaultTargetHesitationMs,
        syncPracticeTiming: savedSession?.syncPracticeTiming ?? true,
        tempoTimingPreferred: savedSession?.tempoTimingPreferred ?? false,
        updatedAt: savedSession?.updatedAt ?? Date.now()
      };
      setSelectedSession(nextSession);
      setSelectedRole(role);
    } catch (error) {
      setStorageStatus(userFacingErrorMessage(error));
      setSelectedSession(null);
    }
  }
}
