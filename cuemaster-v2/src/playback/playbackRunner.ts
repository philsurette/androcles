import type { PlaybackStep } from "./playbackSequence";

export type PlaybackRunnerStatus = {
  label: string;
  detail: string;
  progress: number;
};

export type PlaybackRunnerOptions = {
  resolveAudio: (path: string) => Blob | undefined;
  onStatus: (status: PlaybackRunnerStatus) => void;
  onAdvance: () => void;
  onDone: () => void;
};

export class PlaybackRunner {
  private readonly options: PlaybackRunnerOptions;
  private abortController: AbortController | undefined;
  private objectUrl: string | undefined;

  constructor(options: PlaybackRunnerOptions) {
    this.options = options;
  }

  async run(steps: PlaybackStep[]): Promise<void> {
    this.stop();
    this.abortController = new AbortController();
    const signal = this.abortController.signal;

    for (let index = 0; index < steps.length; index += 1) {
      if (signal.aborted) {
        return;
      }

      const step = steps[index];
      this.options.onStatus({
        label: step.label,
        detail: `${index + 1}/${steps.length}`,
        progress: Math.round((index / Math.max(steps.length, 1)) * 100)
      });

      if (step.kind === "audio") {
        await this.playAudio(step.audioPath, step.durationMs, signal);
      } else if (step.kind === "wait") {
        await this.wait(step.durationMs, signal);
      } else {
        this.options.onAdvance();
      }
    }

    if (!signal.aborted) {
      this.options.onStatus({ label: "Ready", detail: "Sequence complete", progress: 100 });
      this.options.onDone();
    }
  }

  stop(): void {
    this.abortController?.abort();
    this.abortController = undefined;
    this.revokeObjectUrl();
  }

  private async playAudio(path: string, fallbackDurationMs: number, signal: AbortSignal): Promise<void> {
    const blob = this.options.resolveAudio(path);
    if (blob === undefined) {
      await this.wait(Math.min(fallbackDurationMs, 1200), signal);
      return;
    }

    this.revokeObjectUrl();
    this.objectUrl = URL.createObjectURL(blob);
    const audio = new Audio(this.objectUrl);
    await audio.play();
    await new Promise<void>((resolve) => {
      const finish = () => resolve();
      audio.addEventListener("ended", finish, { once: true });
      audio.addEventListener("error", finish, { once: true });
      signal.addEventListener(
        "abort",
        () => {
          audio.pause();
          finish();
        },
        { once: true }
      );
    });
  }

  private wait(durationMs: number, signal: AbortSignal): Promise<void> {
    return new Promise((resolve) => {
      const timeout = window.setTimeout(resolve, Math.max(0, durationMs));
      signal.addEventListener(
        "abort",
        () => {
          window.clearTimeout(timeout);
          resolve();
        },
        { once: true }
      );
    });
  }

  private revokeObjectUrl(): void {
    if (this.objectUrl !== undefined) {
      URL.revokeObjectURL(this.objectUrl);
      this.objectUrl = undefined;
    }
  }
}
