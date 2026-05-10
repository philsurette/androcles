import { useState } from "react";
import type { Playbook } from "../domain/playbook";
import type { Role } from "../domain/role";
import type { RehearsalSession } from "../domain/session";
import { sessionRepository } from "../storage/sessionRepository";
import { LibraryScreen } from "../ui/screens/LibraryScreen";
import { RehearsalScreen } from "../ui/screens/RehearsalScreen";
import { RoleSelectScreen } from "../ui/screens/RoleSelectScreen";

export function App() {
  const [selectedPlaybook, setSelectedPlaybook] = useState<Playbook | null>(null);
  const [selectedRole, setSelectedRole] = useState<Role | null>(null);
  const [selectedSession, setSelectedSession] = useState<RehearsalSession | null>(null);

  if (selectedPlaybook && selectedRole) {
    return (
      <RehearsalScreen
        playbook={selectedPlaybook}
        role={selectedRole}
        initialSession={selectedSession}
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
    const latestSession = await sessionRepository.getLatestForPlaybook(playbook.id);
    const latestRole = latestSession
      ? playbook.roles.find((candidate) => candidate.id === latestSession.roleId)
      : undefined;

    setSelectedPlaybook(playbook);
    setSelectedRole(latestRole ?? null);
    setSelectedSession(latestRole ? (latestSession ?? null) : null);
  }

  async function selectRole(playbook: Playbook, role: Role) {
    setSelectedRole(role);
    setSelectedSession((await sessionRepository.get(playbook.id, role.id)) ?? null);
  }
}
