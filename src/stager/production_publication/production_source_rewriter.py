from __future__ import annotations

from dataclasses import dataclass
from dataclasses import replace

from stager.scriptwright.production_script import ProductionScript
from stager.scriptwright.scriptwright import ScriptWright
from stager.shared import paths


@dataclass
class ProductionSourceRewriter:
    paths_config: paths.PathConfig

    def rewrite_ids(self, production: ProductionScript, id_updates: dict[str, str]) -> ProductionScript:
        updated_entries = []
        for entry in production.entries:
            if entry.production_id in id_updates:
                updated_entries.append(replace(entry, production_id=id_updates[entry.production_id]))
            else:
                updated_entries.append(entry)
        return ProductionScript(metadata=dict(production.metadata), entries=tuple(updated_entries))

    def write_locked(self, production: ProductionScript) -> None:
        text = ScriptWright(paths_config=self.paths_config).render_locked_production(production)
        self.paths_config.production_markdown.write_text(text, encoding="utf-8")
