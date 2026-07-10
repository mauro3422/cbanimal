export class ToastNotification {
  public readonly element: HTMLDivElement;

  private timer: ReturnType<typeof setTimeout> | null = null;

  constructor() {
    this.element = document.createElement("div");
    this.element.className = "toast";
    this.element.style.display = "none";
  }

  public show(message: string, durationMs = 3000): void {
    if (this.timer) {
      clearTimeout(this.timer);
    }

    this.element.textContent = message;
    this.element.style.display = "block";
    this.element.classList.remove("toast--out");

    this.timer = setTimeout(() => {
      this.element.classList.add("toast--out");

      this.timer = setTimeout(() => {
        this.element.style.display = "none";
      }, 200);
    }, durationMs);
  }
}
