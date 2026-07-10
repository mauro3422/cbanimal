import * as THREE from "three";
import { InputManager } from "../input/InputManager";
import { CharacterModel } from "./CharacterModel";
import { CharacterState } from "./CharacterState";

export class Player {
  public readonly object: THREE.Group;

  private readonly characterModel: CharacterModel;
  private readonly input = new InputManager();
  private readonly camera: THREE.Camera;
  private readonly colliders: THREE.Box3[];
  private readonly speed = 4;
  private readonly mapLimit: number;

  private readonly colliderHalfSize = new THREE.Vector3(0.4, 0.9, 0.4);
  private readonly playerCollider = new THREE.Box3();

  private readonly cameraForward = new THREE.Vector3();
  private readonly cameraRight = new THREE.Vector3();
  private readonly movementDirection = new THREE.Vector3();

  private readonly targetQuaternion = new THREE.Quaternion();
  private readonly rotationEuler = new THREE.Euler();

  private moveTarget: THREE.Vector3 | null = null;

  private currentState: CharacterState = CharacterState.Idle;
  private isSitting = false;

  private emoteTimer: ReturnType<typeof setTimeout> | null = null;

  constructor(
    camera: THREE.Camera,
    colliders: THREE.Box3[],
    mapLimit: number,
  ) {
    this.camera = camera;
    this.colliders = colliders;
    this.mapLimit = mapLimit;
    this.object = new THREE.Group();

    this.characterModel = new CharacterModel();
    this.object.add(this.characterModel.object);

    void this.characterModel.load({
      url: "/assets/models/characters/axolotl/axolotl.glb",
      scale: 1,
      rotationY: 0,
      yOffset: 0,
    });
  }

  public get character(): CharacterModel {
    return this.characterModel;
  }

  public getPlayerCollider(): THREE.Box3 {
    return this.playerCollider;
  }

  public getState(): CharacterState {
    return this.currentState;
  }

  public setInputEnabled(enabled: boolean): void {
    this.input.setEnabled(enabled);
  }

  public setMoveTarget(target: THREE.Vector3): void {
    if (this.isSitting || this.emoteTimer) {
      return;
    }

    this.moveTarget = target.clone();

    this.moveTarget.x = THREE.MathUtils.clamp(
      this.moveTarget.x,
      -this.mapLimit,
      this.mapLimit,
    );
    this.moveTarget.z = THREE.MathUtils.clamp(
      this.moveTarget.z,
      -this.mapLimit,
      this.mapLimit,
    );
  }

  public clearMoveTarget(): void {
    this.moveTarget = null;
  }

  public playEmote(emoteId: string): void {
    if (this.isSitting) {
      return;
    }

    if (this.emoteTimer) {
      clearTimeout(this.emoteTimer);
    }

    this.characterModel.play(emoteId, 0.1);

    this.emoteTimer = setTimeout(() => {
      if (!this.isSitting) {
        this.currentState = CharacterState.Idle;
        this.characterModel.setState(CharacterState.Idle);
      }

      this.emoteTimer = null;
    }, 3000);
  }

  public enterSitState(
    sitPosition: THREE.Vector3,
    sitRotation: number,
  ): void {
    this.isSitting = true;
    this.moveTarget = null;
    this.movementDirection.set(0, 0, 0);

    this.object.position.copy(sitPosition);
    this.object.position.y = 0;

    this.rotationEuler.set(0, sitRotation, 0);
    this.targetQuaternion.setFromEuler(this.rotationEuler);
    this.object.quaternion.copy(this.targetQuaternion);

    this.currentState = CharacterState.Sitting;
    this.characterModel.setState(CharacterState.Sitting);
  }

  public exitSitState(): void {
    this.isSitting = false;
    this.currentState = CharacterState.Idle;
    this.characterModel.setState(CharacterState.Idle);
  }

  public update(deltaTime: number): void {
    this.characterModel.update(deltaTime);

    if (this.isSitting || this.emoteTimer) {
      return;
    }

    if (this.moveTarget) {
      this.movementDirection
        .copy(this.moveTarget)
        .sub(this.object.position);

      this.movementDirection.y = 0;

      if (this.movementDirection.length() < 0.5) {
        this.moveTarget = null;
        this.movementDirection.set(0, 0, 0);
      } else {
        this.movementDirection.normalize();
      }
    } else {
      const input = this.input.getMovementInput();

      if (input.lengthSq() === 0) {
        if (this.currentState !== CharacterState.Idle) {
          this.currentState = CharacterState.Idle;
          this.characterModel.setState(CharacterState.Idle);
        }

        return;
      }

      this.camera.getWorldDirection(this.cameraForward);

      this.cameraForward.y = 0;
      this.cameraForward.normalize();

      this.cameraRight
        .crossVectors(
          this.cameraForward,
          this.camera.up,
        )
        .normalize();

      this.movementDirection
        .set(0, 0, 0)
        .addScaledVector(
          this.cameraForward,
          input.y,
        )
        .addScaledVector(
          this.cameraRight,
          input.x,
        )
        .normalize();
    }

    const isMoving = this.movementDirection.lengthSq() > 0;

    if (isMoving) {
      if (this.currentState !== CharacterState.Walking) {
        this.currentState = CharacterState.Walking;
        this.characterModel.setState(CharacterState.Walking);
      }
    } else {
      if (this.currentState !== CharacterState.Idle) {
        this.currentState = CharacterState.Idle;
        this.characterModel.setState(CharacterState.Idle);
      }
    }

    const newPosition = this.object.position.clone();
    newPosition.x += this.movementDirection.x * this.speed * deltaTime;
    newPosition.z += this.movementDirection.z * this.speed * deltaTime;

    newPosition.x = THREE.MathUtils.clamp(
      newPosition.x,
      -this.mapLimit,
      this.mapLimit,
    );
    newPosition.z = THREE.MathUtils.clamp(
      newPosition.z,
      -this.mapLimit,
      this.mapLimit,
    );

    this.updateCollider(newPosition);

    const hasCollision = this.colliders.some(
      (collider) =>
        this.playerCollider.intersectsBox(collider),
    );

    if (!hasCollision) {
      this.object.position.copy(newPosition);
    }

    if (isMoving) {
      const targetRotation = Math.atan2(
        this.movementDirection.x,
        this.movementDirection.z,
      );

      this.rotationEuler.set(0, targetRotation, 0);
      this.targetQuaternion.setFromEuler(this.rotationEuler);

      this.object.quaternion.slerp(
        this.targetQuaternion,
        1 - Math.pow(0.001, deltaTime),
      );
    }
  }

  private updateCollider(
    position: THREE.Vector3,
  ): void {
    this.playerCollider.min.set(
      position.x - this.colliderHalfSize.x,
      position.y,
      position.z - this.colliderHalfSize.z,
    );

    this.playerCollider.max.set(
      position.x + this.colliderHalfSize.x,
      position.y + this.colliderHalfSize.y * 2,
      position.z + this.colliderHalfSize.z,
    );
  }
}
