import * as THREE from "three";
import type { Disposable } from "../../core/Disposable";

function isEditableTarget(target: EventTarget | null): boolean {
  return target instanceof HTMLInputElement
    || target instanceof HTMLTextAreaElement
    || target instanceof HTMLSelectElement
    || (target instanceof HTMLElement && target.isContentEditable);
}

export class InputManager implements Disposable {
  private readonly pressedKeys = new Set<string>();
  private inputEnabled = true;

  constructor() {
    window.addEventListener("keydown", this.handleKeyDown);
    window.addEventListener("keyup", this.handleKeyUp);
  }

  public setEnabled(enabled: boolean): void {
    this.inputEnabled = enabled;

    if (!enabled) {
      this.pressedKeys.clear();
    }
  }

  public getMovementInput(): THREE.Vector2 {
    if (!this.inputEnabled) {
      return new THREE.Vector2();
    }

    const input = new THREE.Vector2();

    if (this.pressedKeys.has("KeyW")) input.y += 1;
    if (this.pressedKeys.has("KeyS")) input.y -= 1;
    if (this.pressedKeys.has("KeyA")) input.x -= 1;
    if (this.pressedKeys.has("KeyD")) input.x += 1;

    if (input.lengthSq() > 1) {
      input.normalize();
    }

    return input;
  }

  public dispose(): void {
    window.removeEventListener("keydown", this.handleKeyDown);
    window.removeEventListener("keyup", this.handleKeyUp);
    this.pressedKeys.clear();
  }

  private handleKeyDown = (event: KeyboardEvent): void => {
    if (!this.inputEnabled || isEditableTarget(event.target)) {
      return;
    }

    this.pressedKeys.add(event.code);
  };

  private handleKeyUp = (event: KeyboardEvent): void => {
    this.pressedKeys.delete(event.code);
  };
}
