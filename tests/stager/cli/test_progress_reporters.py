from __future__ import annotations

from stager.cli.build import RichPlaybookProgressReporter, RichProgressReporter


class FakeProgress:
    def __init__(self) -> None:
        self.added_tasks: list[dict[str, object]] = []
        self.updates: list[dict[str, object]] = []
        self.stopped: list[int] = []

    def add_task(self, description: str, *, total: int) -> int:
        self.added_tasks.append({"description": description, "total": total})
        return len(self.added_tasks)

    def update(self, task_id: int, **kwargs: object) -> None:
        self.updates.append({"task_id": task_id, **kwargs})

    def stop_task(self, task_id: int) -> None:
        self.stopped.append(task_id)


def test_rich_progress_reporter_marks_task_complete_on_finish() -> None:
    progress = FakeProgress()
    reporter = RichProgressReporter(progress)  # type: ignore[arg-type]

    reporter.start(4, "Building")
    reporter.advance("Step 1")
    reporter.finish("Built")

    assert progress.updates[-1] == {"task_id": 1, "description": "Built", "completed": 4}
    assert progress.stopped == [1]


def test_rich_playbook_progress_reporter_marks_task_complete_on_finish() -> None:
    progress = FakeProgress()
    reporter = RichPlaybookProgressReporter(progress)  # type: ignore[arg-type]

    reporter.start_audio_packaging(3)
    reporter.audio_packaged("MEGAERA", "0_1_1", "response")
    reporter.finish_audio_packaging()

    assert progress.updates[-1] == {
        "task_id": 1,
        "description": "Packaged Playbook audio",
        "completed": 3,
    }
    assert progress.stopped == [1]
