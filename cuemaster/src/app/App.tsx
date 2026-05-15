import { useState } from "react";
import type { Playbook } from "../domain/playbook";
import type { Role } from "../domain/role";
import type { RehearsalSession } from "../domain/session";
import { indexedDbStorage } from "../storage/indexedDbStorage";
import { LibraryScreen } from "../ui/screens/LibraryScreen";
import { RehearsalScreen } from "../ui/screens/RehearsalScreen";
import { RoleSelectScreen } from "../ui/screens/RoleSelectScreen";
import { PlayPageScreen } from "../ui/screens/PlayPageScreen";
import { PlaybookInfoScreen } from "../ui/screens/PlaybookInfoScreen";
import { userFacingErrorMessage } from "../ui/errors/userFacingErrorMessage";

export function App() {
  const [selectedPlaybook, setSelectedPlaybook] = useState<Playbook | null>(null);
  const [selectedRole, setSelectedRole] = useState<Role | null>(null);
  const [highlightedRoleId, setHighlightedRoleId] = useState<string | null>(null);
  const [returnRoleId, setReturnRoleId] = useState<string | null>(null);
  const [isRoleSelectFromRehearsal, setIsRoleSelectFromRehearsal] = useState(false);
  const [selectedSession, setSelectedSession] = useState<RehearsalSession | null>(null);
  const [storageStatus, setStorageStatus] = useState<string>("");
  const [isPlayPageMode, setIsPlayPageMode] = useState(false);
  const [infoPlaybook, setInfoPlaybook] = useState<Playbook | null>(null);

  if (infoPlaybook) {
    return (
      <PlaybookInfoScreen
        playbook={infoPlaybook}
        onBack={() => setInfoPlaybook(null)}
      />
    );
  }

  if (selectedPlaybook && isPlayPageMode) {
    return (
      <PlayPageScreen
        playbook={selectedPlaybook}
        onBack={() => {
          setSelectedPlaybook(null);
          setSelectedRole(null);
          setSelectedSession(null);
          setReturnRoleId(null);
          setIsRoleSelectFromRehearsal(false);
          setHighlightedRoleId(null);
          setIsPlayPageMode(false);
        }}
      />
    );
  }

  if (selectedPlaybook && selectedRole) {
    return (
      <RehearsalScreen
        playbook={selectedPlaybook}
        role={selectedRole}
        initialSession={selectedSession}
        initialStorageStatus={storageStatus}
        onBack={() => {
          setSelectedPlaybook(null);
          setSelectedRole(null);
          setSelectedSession(null);
          setIsPlayPageMode(false);
          setReturnRoleId(null);
          setIsRoleSelectFromRehearsal(false);
          setHighlightedRoleId(selectedRole.id);
        }}
        onSelectRole={() => void openRoleSelectFromRehearsal(selectedRole)}
      />
    );
  }

  if (selectedPlaybook) {
    return (
      <RoleSelectScreen
        playbook={selectedPlaybook}
        storageStatus={storageStatus}
        selectedRoleId={highlightedRoleId ?? selectedRole?.id}
        onBack={() => {
          if (isRoleSelectFromRehearsal && returnRoleId) {
            const returnRole = selectedPlaybook.roles.find((candidate) => candidate.id === returnRoleId) ?? null;
            if (returnRole) {
              setSelectedRole(returnRole);
              setReturnRoleId(null);
              setIsRoleSelectFromRehearsal(false);
              setIsPlayPageMode(false);
              return;
            }
          }
          setSelectedPlaybook(null);
          setSelectedRole(null);
          setSelectedSession(null);
          setIsPlayPageMode(false);
          setReturnRoleId(null);
          setIsRoleSelectFromRehearsal(false);
        }}
        onSelectRole={(role) => void selectRole(selectedPlaybook, role)}
      />
    );
  }

  return (
    <LibraryScreen
      onSelectPlaybook={(playbook) => void openPlaybook(playbook)}
      onPlayPlaybook={(playbook) => void openPlayPage(playbook)}
      onViewPlaybookInfo={(playbook) => void openPlaybookInfo(playbook)}
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
    setIsRoleSelectFromRehearsal(false);
    setReturnRoleId(null);
    setSelectedRole(latestRole ?? null);
    setSelectedSession(latestRole ? (latestSession ?? null) : null);
    setIsPlayPageMode(false);
  }

  function openPlayPage(playbook: Playbook) {
    setStorageStatus("");
    setSelectedPlaybook(playbook);
    setHighlightedRoleId(null);
    setIsRoleSelectFromRehearsal(false);
    setReturnRoleId(null);
    setSelectedRole(null);
    setSelectedSession(null);
    setIsPlayPageMode(true);
  }

  function openPlaybookInfo(playbook: Playbook) {
    setStorageStatus("");
    setSelectedPlaybook(null);
    setSelectedRole(null);
    setSelectedSession(null);
    setIsRoleSelectFromRehearsal(false);
    setReturnRoleId(null);
    setHighlightedRoleId(null);
    setIsPlayPageMode(false);
    setInfoPlaybook(playbook);
  }

  async function openRoleSelectFromRehearsal(role: Role | null) {
    if (!role) {
      return;
    }

    setStorageStatus("");
    setReturnRoleId(role.id);
    setIsRoleSelectFromRehearsal(true);
    setSelectedRole(null);
    setIsPlayPageMode(false);
  }

  async function selectRole(playbook: Playbook, role: Role) {
    setStorageStatus("");
    try {
      const savedSession = (await indexedDbStorage.sessions.get(playbook.id, role.id)) ?? null;
      setSelectedRole(role);
      setHighlightedRoleId(role.id);
      setSelectedSession(savedSession);
      setReturnRoleId(null);
      setIsRoleSelectFromRehearsal(false);
      setIsPlayPageMode(false);
    } catch (error) {
      setStorageStatus(userFacingErrorMessage(error));
      setSelectedSession(null);
    }
  }
}
