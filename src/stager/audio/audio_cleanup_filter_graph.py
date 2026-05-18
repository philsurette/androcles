from __future__ import annotations

from dataclasses import dataclass, field

from stager.audio.audio_cleanup_config import CleanupProfile


@dataclass(frozen=True)
class CompiledCleanupFilterGraph:
    filters: tuple[str, ...]
    missing_optional_filters: tuple[str, ...] = ()
    duration_preserving: bool = True

    def filter_spec(self) -> str:
        return ",".join(self.filters)


@dataclass
class AudioCleanupFilterGraphCompiler:
    available_filters: set[str] = field(default_factory=set)

    def compile(self, profile: CleanupProfile) -> CompiledCleanupFilterGraph:
        filters: list[str] = []
        missing: list[str] = []
        self._compile_declick(profile.declick, filters, missing)
        self._compile_deesser(profile.deesser, filters, missing)
        self._compile_denoise(profile.denoise, filters, missing)
        self._compile_gate(profile.gate, filters, missing)
        return CompiledCleanupFilterGraph(
            filters=tuple(filters),
            missing_optional_filters=tuple(missing),
            duration_preserving=True,
        )

    def _compile_declick(self, level: str, filters: list[str], missing: list[str]) -> None:
        if level == "none":
            return
        if not self._has("adeclick", missing):
            return
        if level == "gentle":
            filters.append("adeclick")
            return
        if level == "medium":
            filters.append("adeclick=w=80:o=80")
            return
        raise RuntimeError(f"Unsupported declick level: {level}")

    def _compile_deesser(self, level: str, filters: list[str], missing: list[str]) -> None:
        if level == "none":
            return
        if not self._has("deesser", missing):
            return
        if level == "gentle":
            filters.append("deesser=i=0.25")
            return
        if level == "medium":
            filters.append("deesser=i=0.45")
            return
        raise RuntimeError(f"Unsupported deesser level: {level}")

    def _compile_denoise(self, level: str, filters: list[str], missing: list[str]) -> None:
        if level == "none":
            return
        if level == "light":
            if self._has("afftdn", missing):
                filters.append("afftdn=nr=6:nf=-50")
            return
        if level == "medium":
            if self._has("afftdn", missing):
                filters.append("afftdn=nr=10:nf=-50")
            return
        if level == "wavelet":
            if self._has("afwtdn", missing):
                filters.append("afwtdn=sigma=-45dB")
            return
        if level == "nlmeans":
            if self._has("anlmdn", missing):
                filters.append("anlmdn=s=0.00001")
            return
        raise RuntimeError(f"Unsupported denoise level: {level}")

    def _compile_gate(self, level: str, filters: list[str], missing: list[str]) -> None:
        if level == "none":
            return
        if not self._has("agate", missing):
            return
        if level == "gentle":
            filters.append("agate=threshold=0.02:ratio=1.5:attack=20:release=250")
            return
        raise RuntimeError(f"Unsupported gate level: {level}")

    def _has(self, name: str, missing: list[str]) -> bool:
        if not self.available_filters or name in self.available_filters:
            return True
        missing.append(name)
        return False
