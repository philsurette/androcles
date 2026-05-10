import { useState } from "react";
import type { Playbook } from "../domain/playbook";
import type { Role } from "../domain/role";
import { LibraryScreen } from "../ui/screens/LibraryScreen";
import { RehearsalScreen } from "../ui/screens/RehearsalScreen";
import { RoleSelectScreen } from "../ui/screens/RoleSelectScreen";

export function App() {
  const [selectedPlaybook, setSelectedPlaybook] = useState<Playbook | null>(null);
  const [selectedRole, setSelectedRole] = useState<Role | null>(null);

  if (selectedPlaybook && selectedRole) {
    return <RehearsalScreen playbook={selectedPlaybook} role={selectedRole} onBack={() => setSelectedRole(null)} />;
  }

  if (selectedPlaybook) {
    return (
      <RoleSelectScreen
        playbook={selectedPlaybook}
        onBack={() => setSelectedPlaybook(null)}
        onSelectRole={setSelectedRole}
      />
    );
  }

  return (
    <LibraryScreen
      onSelectPlaybook={(playbook) => {
        setSelectedPlaybook(playbook);
        setSelectedRole(null);
      }}
    />
  );
}
