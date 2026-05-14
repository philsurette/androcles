import { useState } from "react";
import type { Playbook } from "../domain/playbook";
import type { Role } from "../domain/role";
import type { RehearsalSession } from "../domain/session";
import { indexedDbStorage } from "../storage/indexedDbStorage";
import { LibraryScreen } from "../ui/screens/LibraryScreen";
import { RehearsalScreen } from "../ui/screens/RehearsalScreen";
import { RoleSelectScreen } from "../ui/screens/RoleSelectScreen";
import { userFacingErrorMessage } from "../ui/errors/userFacingErrorMessage";

export function App() {
  const [selectedPlaybook, setSelectedPlaybook] = useState<Playbook | null>(null);
  const [selectedRole, setSelectedRole] = useState<Role | null>(null);
  const [highlightedRoleId, setHighlightedRoleId] = useState<string | null>(null);
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
        selectedRoleId={highlightedRoleId ?? selectedRole?.id}
        onBack={() => setSelectedPlaybook(null)}
        onSelectRole={(role) => void selectRole(selectedPlaybook, role)}
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
    setHighlightedRoleId(latestRole?.id ?? null);
    setSelectedRole(latestRole ?? null);
    setSelectedSession(latestRole ? (latestSession ?? null) : null);
  }

  async function selectRole(playbook: Playbook, role: Role) {
    setStorageStatus("");
    try {
      const savedSession = (await indexedDbStorage.sessions.get(playbook.id, role.id)) ?? null;
      setSelectedRole(role);
      setHighlightedRoleId(role.id);
      setSelectedSession(savedSession);
    } catch (error) {
      setStorageStatus(userFacingErrorMessage(error));
      setSelectedSession(null);
    }
  }
}
