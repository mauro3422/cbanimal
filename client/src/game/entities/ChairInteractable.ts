import * as THREE from "three";
import type { Player } from "./Player";
import type { IInteractable } from "./IInteractable";

export class ChairInteractable implements IInteractable {
  public readonly object: THREE.Group;
  public readonly interactionDistance = 2;
  public interactionText = "Sentarse";

  private readonly sitPosition: THREE.Vector3;
  private readonly sitRotation: number;
  private isOccupied = false;

  constructor(
    position: THREE.Vector3,
    rotationY: number,
  ) {
    this.sitPosition = position.clone();
    this.sitRotation = rotationY;
    this.object = new THREE.Group();

    const seat = new THREE.Mesh(
      new THREE.BoxGeometry(1.2, 0.15, 0.8),
      new THREE.MeshStandardMaterial({ color: 0x8b5e3c }),
    );

    seat.position.y = 0.4;
    seat.castShadow = true;
    seat.receiveShadow = true;

    this.object.add(seat);

    const backrest = new THREE.Mesh(
      new THREE.BoxGeometry(1.2, 0.8, 0.15),
      new THREE.MeshStandardMaterial({ color: 0x6b3f2a }),
    );

    backrest.position.set(0, 0.85, -0.35);
    backrest.castShadow = true;
    backrest.receiveShadow = true;

    this.object.add(backrest);

    this.object.position.copy(position);
    this.object.rotation.y = rotationY;
  }

  public interact(player: Player): void {
    if (this.isOccupied) {
      player.exitSitState();
      this.interactionText = "Sentarse";
      this.isOccupied = false;
    } else {
      player.enterSitState(this.sitPosition, this.sitRotation);
      this.interactionText = "Levantarse";
      this.isOccupied = true;
    }
  }
}
