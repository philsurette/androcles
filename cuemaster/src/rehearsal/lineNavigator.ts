export class LineNavigator {
  next(index: number, total: number): number {
    return Math.min(index + 1, Math.max(total - 1, 0));
  }

  previous(index: number): number {
    return Math.max(index - 1, 0);
  }
}
