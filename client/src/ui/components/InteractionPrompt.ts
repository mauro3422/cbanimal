export class InteractionPrompt {
  public readonly element: HTMLDivElement;

  constructor() {
    this.element = document.createElement("div");
    this.element.className = "interaction-prompt";
    this.hide();
  }

  public show(
    key: string,
    action: string,
  ): void {
    this.element.innerHTML = `
      <kbd>${key}</kbd>
      <span>${action}</span>
    `;

    this.element.hidden = false;
  }

  public hide(): void {
    this.element.hidden = true;
  }
}
