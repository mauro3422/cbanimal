import * as THREE from "three";

export class InputManager {
  private readonly pressedKeys = new Set<string>();
  private inputEnabled = true;

  constructor() {
    window.addEventListener("keydown", (event) => {
      this.pressedKeys.add(event.code);
    });

    window.addEventListener("keyup", (event) => {
      this.pressedKeys.delete(event.code);
    });
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
}
