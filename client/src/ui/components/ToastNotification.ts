import type { Disposable } from "../../core/Disposable";

export class ToastNotification implements Disposable {
  public readonly element: HTMLDivElement;

  private timer: ReturnType<typeof setTimeout> | null = null;

  constructor() {
    this.element = document.createElement("div");
    this.element.className = "toast";
    this.element.style.display = "none";
  }

  public show(message: string, durationMs = 3000): void {
    this.clearTimer();

    this.element.textContent = message;
    this.element.style.display = "block";
    this.element.classList.remove("toast--out");

    this.timer = setTimeout(() => {
      this.element.classList.add("toast--out");

      this.timer = setTimeout(() => {
        this.element.style.display = "none";
        this.timer = null;
      }, 200);
    }, durationMs);
  }

  public dispose(): void {
    this.clearTimer();
    this.element.remove();
  }

  private clearTimer(): void {
    if (!this.timer) {
      return;
    }

    clearTimeout(this.timer);
    this.timer = null;
  }
}
