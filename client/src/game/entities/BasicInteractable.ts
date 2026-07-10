import * as THREE from "three";
import type { Player } from "./Player";
import type { IInteractable } from "./IInteractable";

export class BasicInteractable implements IInteractable {
  public readonly object: THREE.Mesh;
  public readonly interactionDistance = 2.5;
  public interactionText = "Presioná E para interactuar";

  private readonly message: string;

  constructor(
    position: THREE.Vector3,
    message: string,
  ) {
    this.message = message;
    this.object = new THREE.Mesh(
      new THREE.BoxGeometry(1.5, 1.5, 1.5),
      new THREE.MeshStandardMaterial({
        color: 0x4f6d8a,
      }),
    );

    this.object.position.copy(position);
    this.object.position.y = 0.75;
    this.object.castShadow = true;
    this.object.receiveShadow = true;
  }

  public interact(_player: Player): void {
    console.log(this.message);

    const material = this.object.material;

    if (material instanceof THREE.MeshStandardMaterial) {
      material.color.setHex(Math.random() * 0xffffff);
    }
  }
}
