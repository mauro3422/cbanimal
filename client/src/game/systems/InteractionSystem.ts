import type { IInteractable } from "../entities/IInteractable";
import type { Player } from "../entities/Player";
import type { InteractionPrompt } from "../../ui/components/InteractionPrompt";

export class InteractionSystem {
  private currentInteractable: IInteractable | null = null;
  private interactionPressed = false;

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

  private handleKeyDown = (event: KeyboardEvent): void => {
    if (event.code === "KeyE" && !this.interactionPressed) {
      this.interactionPressed = true;
      this.currentInteractable?.interact(this.player);
    }
  };

  private handleKeyUp = (event: KeyboardEvent): void => {
    if (event.code === "KeyE") {
      this.interactionPressed = false;
    }
  };

  public update(): void {
    this.currentInteractable = null;

    let closestDistance = Infinity;

    for (const interactable of this.interactables) {
      const distance = this.player.object.position.distanceTo(
        interactable.object.position,
      );

      if (distance < interactable.interactionDistance && distance < closestDistance) {
        closestDistance = distance;
        this.currentInteractable = interactable;
      }
    }

    this.updatePrompt();
  }

  private updatePrompt(): void {
    if (this.currentInteractable) {
      this.prompt.show("E", this.currentInteractable.interactionText);
    } else {
      this.prompt.hide();
    }
  }
}
