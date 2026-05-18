from __future__ import annotations

from dataclasses import dataclass, field

from stager.audio.audio_cleanup_config import CleanupProfile


@dataclass(frozen=True)
class CompiledCleanupFilterGraph:
    filters: tuple[str, ...]
    missing_optional_filters: tuple[str, ...] = ()
    duration_preserving: bool = True
    filter_safety: dict[str, bool] = field(default_factory=dict)

    def filter_spec(self) -> str:
        return ",".join(self.filters)


@dataclass
class AudioCleanupFilterGraphCompiler:
    available_filters: set[str] = field(default_factory=set)

    def compile(self, profile: CleanupProfile) -> CompiledCleanupFilterGraph:
        filters: list[str] = []
        missing: list[str] = []
        safety: dict[str, bool] = {}
        self._compile_declick(profile.declick, filters, missing, safety)
        self._compile_deesser(profile.deesser, filters, missing, safety)
        self._compile_denoise(profile.denoise, filters, missing, safety)
        self._compile_gate(profile.gate, filters, missing, safety)
        return CompiledCleanupFilterGraph(
            filters=tuple(filters),
            missing_optional_filters=tuple(missing),
            duration_preserving=all(safety.values()),
            filter_safety=safety,
        )

    def _compile_declick(
        self,
        level: str,
        filters: list[str],
        missing: list[str],
        safety: dict[str, bool],
    ) -> None:
        if level == "none":
            return
        if not self._has("adeclick", missing):
            return
        if level == "gentle":
            filters.append("adeclick")
            safety["adeclick"] = True
            return
        if level == "medium":
            filters.append("adeclick=w=80:o=80")
            safety["adeclick"] = True
            return
        raise RuntimeError(f"Unsupported declick level: {level}")

    def _compile_deesser(
        self,
        level: str,
        filters: list[str],
        missing: list[str],
        safety: dict[str, bool],
    ) -> None:
        if level == "none":
            return
        if not self._has("deesser", missing):
            return
        if level == "gentle":
            filters.append("deesser=i=0.25")
            safety["deesser"] = True
            return
        if level == "medium":
            filters.append("deesser=i=0.45")
            safety["deesser"] = True
            return
        raise RuntimeError(f"Unsupported deesser level: {level}")

    def _compile_denoise(
        self,
        level: str,
        filters: list[str],
        missing: list[str],
        safety: dict[str, bool],
    ) -> None:
        if level == "none":
            return
        if level == "light":
            if self._has("afftdn", missing):
                filters.append("afftdn=nr=6:nf=-50")
                safety["afftdn"] = True
            return
        if level == "medium":
            if self._has("afftdn", missing):
                filters.append("afftdn=nr=10:nf=-50")
                safety["afftdn"] = True
            return
        if level == "wavelet":
            if self._has("afwtdn", missing):
                filters.append("afwtdn=sigma=-45dB")
                safety["afwtdn"] = True
            return
        if level == "nlmeans":
            if self._has("anlmdn", missing):
                filters.append("anlmdn=s=0.00001")
                safety["anlmdn"] = True
            return
        raise RuntimeError(f"Unsupported denoise level: {level}")

    def _compile_gate(
        self,
        level: str,
        filters: list[str],
        missing: list[str],
        safety: dict[str, bool],
    ) -> None:
        if level == "none":
            return
        if not self._has("agate", missing):
            return
        if level == "gentle":
            filters.append("agate=threshold=0.02:ratio=1.5:attack=20:release=250")
            safety["agate"] = True
            return
        raise RuntimeError(f"Unsupported gate level: {level}")

    def _has(self, name: str, missing: list[str]) -> bool:
        if not self.available_filters or name in self.available_filters:
            return True
        missing.append(name)
        return False
