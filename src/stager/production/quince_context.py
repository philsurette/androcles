from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import os

from ruamel.yaml import YAML

from stager.shared import paths
from stager.shared.play_config import PlayConfig


@dataclass(frozen=True)
class QuinceWorkspaceConfig:
    version: int = 1
    active_play: str | None = None

    def to_dict(self) -> dict:
        data = {"version": self.version}
        if self.active_play is not None:
            data["active_play"] = self.active_play
        return data


@dataclass(frozen=True)
class QuinceContext:
    workspace_root: Path
    play_id: str
    path_config: paths.PathConfig
    selection_source: str
    production_source: str = "working"

    def to_dict(self) -> dict:
        return {
            "workspace_root": self.workspace_root.as_posix(),
            "play_id": self.play_id,
            "play_dir": self.path_config.play_dir.as_posix(),
            "build_dir": self.path_config.build_dir.as_posix(),
            "selection_source": self.selection_source,
            "production_source": self.production_source,
        }


class QuinceContextResolver:
    def __init__(
        self,
        *,
        cwd: Path | None = None,
        workspace: Path | None = None,
        environ: dict[str, str] | None = None,
    ) -> None:
        self.cwd = (cwd or Path.cwd()).resolve()
        self.workspace = workspace
        self.environ = environ if environ is not None else dict(os.environ)

    def resolve(
        self,
        *,
        play_id: str | None = None,
        production_source: str = "working",
    ) -> QuinceContext:
        workspace_root = self.resolve_workspace_root()
        selected_play_id, selection_source = self.resolve_play_id(workspace_root, play_id=play_id)
        return QuinceContext(
            workspace_root=workspace_root,
            play_id=selected_play_id,
            path_config=self._path_config(workspace_root, selected_play_id),
            selection_source=selection_source,
            production_source=production_source,
        )

    def resolve_workspace_root(self) -> Path:
        if self.workspace is not None:
            return self._validated_workspace_root(self.workspace.resolve())
        env_workspace = self.environ.get("QUINCE_WORKSPACE")
        if env_workspace:
            return self._validated_workspace_root(Path(env_workspace).expanduser().resolve())
        for candidate in self._ancestors(self.cwd):
            if (candidate / "quince.yaml").exists():
                return self._validated_workspace_root(candidate)
        for candidate in self._ancestors(self.cwd):
            if (candidate / "plays").is_dir() and (
                (candidate / "play-config.yaml").exists() or (candidate / "pyproject.toml").exists()
            ):
                return self._validated_workspace_root(candidate)
        raise RuntimeError(
            "No Quince workspace found. Run from a workspace containing plays/ or pass --workspace <path>."
        )

    def resolve_play_id(self, workspace_root: Path, *, play_id: str | None = None) -> tuple[str, str]:
        if play_id:
            self._validate_play_exists(workspace_root, play_id)
            return play_id, "explicit"
        inferred = self._infer_play_from_directory(workspace_root)
        if inferred is not None:
            return inferred
        workspace_config = self.load_workspace_config(workspace_root)
        if workspace_config.active_play:
            self._validate_play_exists(workspace_root, workspace_config.active_play)
            return workspace_config.active_play, "quince.yaml"
        play_config_path = workspace_root / "play-config.yaml"
        if play_config_path.exists():
            configured_play = PlayConfig.load(workspace_root).play_id
            self._validate_play_exists(workspace_root, configured_play)
            return configured_play, "play-config.yaml"
        play_ids = self.play_ids(workspace_root)
        if len(play_ids) == 1:
            return play_ids[0], "single-play"
        if not play_ids:
            raise RuntimeError(f"No productions found under {(workspace_root / 'plays').as_posix()}.")
        formatted = ", ".join(play_ids)
        raise RuntimeError(
            f"Multiple productions found: {formatted}. "
            f"Run `quince status --play {play_ids[0]}` or `quince use {play_ids[0]}`."
        )

    def load_workspace_config(self, workspace_root: Path) -> QuinceWorkspaceConfig:
        config_path = workspace_root / "quince.yaml"
        if not config_path.exists():
            return QuinceWorkspaceConfig()
        yaml = YAML(typ="safe", pure=True)
        data = yaml.load(config_path.read_text(encoding="utf-8")) or {}
        if not isinstance(data, dict):
            raise RuntimeError(f"Invalid quince.yaml format: {config_path.as_posix()}")
        version = data.get("version", 1)
        if version != 1:
            raise RuntimeError(f"Unsupported quince.yaml version: {version}")
        active_play = data.get("active_play")
        if active_play is not None and not isinstance(active_play, str):
            raise RuntimeError(f"Invalid active_play in quince.yaml: {active_play!r}")
        return QuinceWorkspaceConfig(version=version, active_play=active_play)

    def save_workspace_config(self, workspace_root: Path, config: QuinceWorkspaceConfig) -> Path:
        config_path = workspace_root / "quince.yaml"
        yaml = YAML()
        yaml.default_flow_style = False
        with config_path.open("w", encoding="utf-8") as output:
            yaml.dump(config.to_dict(), output)
        return config_path

    def play_ids(self, workspace_root: Path) -> list[str]:
        plays_dir = workspace_root / "plays"
        if not plays_dir.exists():
            return []
        return sorted(path.name for path in plays_dir.iterdir() if path.is_dir())

    def _infer_play_from_directory(self, workspace_root: Path) -> tuple[str, str] | None:
        for base_name, source in (("plays", "play-directory"), ("build", "build-directory")):
            base = workspace_root / base_name
            try:
                relative = self.cwd.relative_to(base)
            except ValueError:
                continue
            if not relative.parts:
                continue
            candidate = relative.parts[0]
            self._validate_play_exists(workspace_root, candidate)
            return candidate, source
        return None

    def _validated_workspace_root(self, workspace_root: Path) -> Path:
        if not workspace_root.exists():
            raise RuntimeError(f"Quince workspace does not exist: {workspace_root.as_posix()}")
        if not (workspace_root / "plays").is_dir():
            raise RuntimeError(f"Quince workspace has no plays/ directory: {workspace_root.as_posix()}")
        return workspace_root

    def _validate_play_exists(self, workspace_root: Path, play_id: str) -> None:
        if not (workspace_root / "plays" / play_id).is_dir():
            raise RuntimeError(f"Unknown production `{play_id}` under {(workspace_root / 'plays').as_posix()}.")

    def _path_config(self, workspace_root: Path, play_id: str) -> paths.PathConfig:
        return paths.PathConfig(
            play_name=play_id,
            root=workspace_root / "src",
            build_root=workspace_root / "build",
            plays_dir=workspace_root / "plays",
            snippets_dir=workspace_root / "snippets",
        )

    def _ancestors(self, path: Path) -> list[Path]:
        return [path, *path.parents]
