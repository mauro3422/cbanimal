export class InteractionPrompt {
  public readonly element: HTMLDivElement;

  private readonly keyElement: HTMLElement;
  private readonly actionElement: HTMLSpanElement;

  constructor() {
    this.element = document.createElement("div");
    this.element.className = "interaction-prompt";

    this.keyElement = document.createElement("kbd");
    this.actionElement = document.createElement("span");
    this.element.append(this.keyElement, this.actionElement);
    this.hide();
  }

  public show(key: string, action: string): void {
    this.keyElement.textContent = key;
    this.actionElement.textContent = action;
    this.element.hidden = false;
  }

  public hide(): void {
    this.element.hidden = true;
  }
}
