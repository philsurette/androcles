import { useState } from "react";
import type { Playbook } from "../../domain/playbook";
import type { Role } from "../../domain/role";
import { sectionOptionsForRole } from "../../rehearsal/sectionOptions";

type RoleSelectScreenProps = {
  playbook: Playbook;
  storageStatus?: string;
  onBack: () => void;
  onSelectRole: (role: Role, startLineId?: string) => void;
};

const resumeValue = "__resume";

export function RoleSelectScreen({ playbook, storageStatus = "", onBack, onSelectRole }: RoleSelectScreenProps) {
  const [selectedSectionIds, setSelectedSectionIds] = useState<Record<string, string>>({});

  return (
    <main className="shell">
      <section className="hero library">
        <button type="button" className="secondary" onClick={onBack}>
          Back to Library
        </button>
        <p className="eyebrow">Choose Role</p>
        <h1>{playbook.title}</h1>
        <p>Select the role you want Cuemaster to prompt.</p>
        {storageStatus ? (
          <p className="error" role="alert">
            {storageStatus}
          </p>
        ) : null}

        <ul className="role-list">
          {playbook.roles.map((role) => {
            const sectionOptions = sectionOptionsForRole(playbook, role);
            const selectedSectionId = selectedSectionIds[role.id] ?? resumeValue;
            const selectedSection = sectionOptions.find((section) => section.id === selectedSectionId);

            return (
              <li className="playbook-row" key={role.id}>
                <div>
                  <h3>{role.displayName}</h3>
                  <p>
                    {role.lines.length} line{role.lines.length === 1 ? "" : "s"}
                  </p>
                  {sectionOptions.length > 0 ? (
                    <label className="role-start-setting">
                      Start at
                      <select
                        value={selectedSectionId}
                        onChange={(event) =>
                          setSelectedSectionIds({ ...selectedSectionIds, [role.id]: event.target.value })
                        }
                      >
                        <option value={resumeValue}>Resume saved position / beginning</option>
                        {sectionOptions.map((section) => (
                          <option key={section.id} value={section.id}>
                            {section.title} ({section.lineCount} line{section.lineCount === 1 ? "" : "s"})
                          </option>
                        ))}
                      </select>
                    </label>
                  ) : null}
                </div>
                <button type="button" onClick={() => onSelectRole(role, selectedSection?.startLineId)}>
                  Select
                </button>
              </li>
            );
          })}
        </ul>
      </section>
    </main>
  );
}
