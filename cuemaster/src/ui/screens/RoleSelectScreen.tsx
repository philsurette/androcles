import type { Playbook } from "../../domain/playbook";
import type { Role } from "../../domain/role";

type RoleSelectScreenProps = {
  playbook: Playbook;
  storageStatus?: string;
  selectedRoleId?: string;
  onBack: () => void;
  onSelectRole: (role: Role) => void;
};

export function RoleSelectScreen({
  playbook,
  storageStatus = "",
  selectedRoleId,
  onBack,
  onSelectRole
}: RoleSelectScreenProps) {
  return (
    <main className="shell">
      <section className="hero library">
        <header className="role-select-header rehearsal-header">
          <div className="breadcrumb-row">
            <button
              type="button"
              className="icon-button secondary"
              aria-label="Back to library"
              data-tooltip="Back to library"
              onClick={onBack}
            >
              <span aria-hidden="true">←</span>
            </button>
            <div className="rehearsal-title-stack">
              <p className="rehearsal-play-title">{playbook.title}</p>
              <p className="role-select-subtitle">Choose role</p>
            </div>
          </div>
        </header>
        {storageStatus ? (
          <p className="error" role="alert">
            {storageStatus}
          </p>
        ) : null}

        <div className="role-select-table-header">
          <span className="role-select-table-header-label">Role</span>
          <span className="role-select-table-header-label">Lines</span>
        </div>
        <ul className="role-select-list role-select-listbox" role="listbox" aria-label="Roles">
          {sortedRoles(playbook.roles, selectedRoleId).map((role) => {
            const isSelected = role.id === selectedRoleId;
            return (
              <li
                key={role.id}
                role="option"
                aria-selected={isSelected}
                tabIndex={isSelected ? 0 : -1}
                className={`role-select-item role-select-row${isSelected ? " role-select-item-selected" : ""}`}
                onClick={() => onSelectRole(role)}
                onKeyDown={(event) => {
                  if (event.key === "Enter" || event.key === " ") {
                    event.preventDefault();
                    onSelectRole(role);
                  }
                }}
              >
                <span className="role-select-item-name">{role.displayName}</span>
                <span className="role-select-item-count">
                  {role.lines.length} line{role.lines.length === 1 ? "" : "s"}
                </span>
              </li>
            );
          })}
        </ul>
      </section>
    </main>
  );
}

function sortedRoles(roles: Role[], selectedRoleId?: string): Role[] {
  if (!selectedRoleId) {
    return roles;
  }

  const selectedIndex = roles.findIndex((role) => role.id === selectedRoleId);
  if (selectedIndex < 0) {
    return roles;
  }

  const selected = roles[selectedIndex];
  return [selected, ...roles.slice(0, selectedIndex), ...roles.slice(selectedIndex + 1)];
}
