import { useState } from "react";
import type { Playbook } from "../domain/playbook";
import { LibraryScreen } from "../ui/screens/LibraryScreen";
import { RoleSelectScreen } from "../ui/screens/RoleSelectScreen";

export function App() {
  const [selectedPlaybook, setSelectedPlaybook] = useState<Playbook | null>(null);

  if (selectedPlaybook) {
    return <RoleSelectScreen playbook={selectedPlaybook} onBack={() => setSelectedPlaybook(null)} />;
  }

  return <LibraryScreen onSelectPlaybook={setSelectedPlaybook} />;
}
