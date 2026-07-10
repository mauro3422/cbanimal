import * as THREE from "three";
import type { Player } from "./Player";

export interface IInteractable {
  object: THREE.Object3D;
  interactionDistance: number;
  interactionText: string;

  interact(player: Player): void;
}
