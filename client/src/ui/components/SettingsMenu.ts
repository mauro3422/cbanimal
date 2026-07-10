import { uiEvents } from "../core/UIEventBus";
import type { UIState } from "../state/UIState";

export class SettingsMenu {
  public readonly element: HTMLDivElement;

  private readonly debugCheckbox: HTMLInputElement;
  private readonly state: UIState;

  constructor(state: UIState) {
    this.state = state;

    this.element = document.createElement("div");
    this.element.className = "popup-menu";
    this.element.style.display = "none";

    const backdrop = document.createElement("div");
    backdrop.className = "popup-menu__backdrop";
    backdrop.addEventListener("click", () => this.close());

    this.element.innerHTML = `
      <label class="settings-label">
        <span>Collider debug</span>
        <input type="checkbox" />
      </label>
    `;

    this.debugCheckbox = this.element.querySelector(
      "input",
    )!;

    this.debugCheckbox.addEventListener(
      "change",
      () => {
        this.state.isDebugEnabled =
          this.debugCheckbox.checked;

        uiEvents.emit("settings:toggle-debug", {
          enabled: this.debugCheckbox.checked,
        });
      },
    );

    this.element.appendChild(backdrop);
  }

  public open(): void {
    this.element.style.display = "flex";
    this.state.isSettingsOpen = true;
    this.debugCheckbox.checked = this.state.isDebugEnabled;
  }

  public close(): void {
    this.element.style.display = "none";
    this.state.isSettingsOpen = false;
  }

  public toggle(): void {
    if (this.state.isSettingsOpen) {
      this.close();
    } else {
      this.open();
    }
  }
}
