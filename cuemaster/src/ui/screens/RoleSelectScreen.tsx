import type { Playbook } from "../../domain/playbook";
import type { Role } from "../../domain/role";

type RoleSelectScreenProps = {
  playbook: Playbook;
  onBack: () => void;
  onSelectRole: (role: Role) => void;
};

export function RoleSelectScreen({ playbook, onBack, onSelectRole }: RoleSelectScreenProps) {
  return (
    <main className="shell">
      <section className="hero library">
        <button type="button" className="secondary" onClick={onBack}>
          Back to Library
        </button>
        <p className="eyebrow">Choose Role</p>
        <h1>{playbook.title}</h1>
        <p>Select the role you want Cuemaster to prompt.</p>

        <ul className="role-list">
          {playbook.roles.map((role) => (
            <li className="playbook-row" key={role.id}>
              <div>
                <h3>{role.displayName}</h3>
                <p>
                  {role.lines.length} line{role.lines.length === 1 ? "" : "s"}
                </p>
              </div>
              <button type="button" onClick={() => onSelectRole(role)}>
                Select
              </button>
            </li>
          ))}
        </ul>
      </section>
    </main>
  );
}
