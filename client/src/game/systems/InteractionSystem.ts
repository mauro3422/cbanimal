import type { Disposable } from "../../core/Disposable";
import type { InteractionPrompt } from "../../ui/components/InteractionPrompt";
import type { IInteractable } from "../entities/IInteractable";
import type { Player } from "../entities/Player";

function isEditableTarget(target: EventTarget | null): boolean {
  return target instanceof HTMLInputElement
    || target instanceof HTMLTextAreaElement
    || target instanceof HTMLSelectElement
    || (target instanceof HTMLElement && target.isContentEditable);
}

export class InteractionSystem implements Disposable {
  private currentInteractable: IInteractable | null = null;
  private interactionPressed = false;
  private inputEnabled = true;

  private readonly player: Player;
  private readonly interactables: IInteractable[];
  private readonly prompt: InteractionPrompt;

  constructor(
    player: Player,
    interactables: IInteractable[],
    prompt: InteractionPrompt,
  ) {
    this.player = player;
    this.interactables = interactables;
    this.prompt = prompt;

    window.addEventListener("keydown", this.handleKeyDown);
    window.addEventListener("keyup", this.handleKeyUp);
  }

  public setEnabled(enabled: boolean): void {
    this.inputEnabled = enabled;

    if (!enabled) {
      this.interactionPressed = false;
      this.currentInteractable = null;
      this.prompt.hide();
    }
  }

  public update(): void {
    if (!this.inputEnabled) {
      this.currentInteractable = null;
      this.prompt.hide();
      return;
    }

    this.currentInteractable = null;
    let closestDistance = Infinity;

    for (const interactable of this.interactables) {
      const distance = this.player.object.position.distanceTo(
        interactable.object.position,
      );

      if (
        distance < interactable.interactionDistance
        && distance < closestDistance
      ) {
        closestDistance = distance;
        this.currentInteractable = interactable;
      }
    }

    this.updatePrompt();
  }

  public dispose(): void {
    window.removeEventListener("keydown", this.handleKeyDown);
    window.removeEventListener("keyup", this.handleKeyUp);
    this.currentInteractable = null;
    this.prompt.hide();
  }

  private handleKeyDown = (event: KeyboardEvent): void => {
    if (
      !this.inputEnabled
      || isEditableTarget(event.target)
      || event.code !== "KeyE"
      || this.interactionPressed
    ) {
      return;
    }

    this.interactionPressed = true;
    this.currentInteractable?.interact(this.player);
  };

  private handleKeyUp = (event: KeyboardEvent): void => {
    if (event.code === "KeyE") {
      this.interactionPressed = false;
    }
  };

  private updatePrompt(): void {
    if (this.currentInteractable) {
      this.prompt.show("E", this.currentInteractable.interactionText);
    } else {
      this.prompt.hide();
    }
  }
}
