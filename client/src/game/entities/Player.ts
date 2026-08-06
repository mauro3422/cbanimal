import * as THREE from "three";
import type { Disposable } from "../../core/Disposable";
import { InputManager } from "../input/InputManager";
import { CharacterModel } from "./CharacterModel";
import type {
  CharacterModelConfig,
  WalkingSupportFoot,
} from "./CharacterModel";
import { MovementState } from "./MovementState";
import type { MovementState as MovementStateValue } from "./MovementState";

const CLICK_TARGET_REACHED_DISTANCE = 0.5;
const CLICK_TARGET_BLOCK_TIMEOUT = 0.25;
const TURN_RESPONSE_TIME = 0.16;

export class Player implements Disposable {
  public readonly object: THREE.Group;

  private readonly characterModel: CharacterModel;
  private readonly input = new InputManager();
  private readonly camera: THREE.Camera;
  private readonly colliders: THREE.Box3[];
  // Brisk walk speed; the animation cadence is derived from this value.
  private readonly speed = 2.2;
  private readonly mapLimit: number;

  private readonly colliderHalfSize = new THREE.Vector3(0.4, 0.9, 0.4);
  private readonly playerCollider = new THREE.Box3();

  private readonly cameraForward = new THREE.Vector3();
  private readonly cameraRight = new THREE.Vector3();
  private readonly desiredMovementDirection = new THREE.Vector3();
  private readonly movementDirection = new THREE.Vector3();
  private readonly previousPosition = new THREE.Vector3();
  private readonly supportFootPosition = new THREE.Vector3();
  private readonly supportFootAnchor = new THREE.Vector3();
  private readonly supportFootCorrection = new THREE.Vector3();

  private readonly targetQuaternion = new THREE.Quaternion();
  private readonly rotationEuler = new THREE.Euler();

  private supportFoot: WalkingSupportFoot | null = null;
  private moveTarget: THREE.Vector3 | null = null;
  private blockedTime = 0;

  private movementState: MovementStateValue = MovementState.Idle;
  private activeEmote: string | null = null;
  private isSitting = false;
  private emoteTimer: ReturnType<typeof setTimeout> | null = null;

  constructor(
    camera: THREE.Camera,
    colliders: THREE.Box3[],
    mapLimit: number,
    modelConfig: CharacterModelConfig | null,
  ) {
    this.camera = camera;
    this.colliders = colliders;
    this.mapLimit = mapLimit;
    this.object = new THREE.Group();
    this.characterModel = new CharacterModel();
    this.characterModel.setWalkingSpeed(this.speed);
    this.object.add(this.characterModel.object);
    this.updateCollider(this.object.position);

    if (modelConfig) {
      void this.characterModel.load(modelConfig).then(() => {
        this.syncAnimationAfterLoad();
      });
    }
  }

  public get character(): CharacterModel {
    return this.characterModel;
  }

  public getPlayerCollider(): THREE.Box3 {
    return this.playerCollider;
  }

  public getMovementState(): MovementStateValue {
    return this.movementState;
  }

  public getActiveEmote(): string | null {
    return this.activeEmote;
  }

  public setInputEnabled(enabled: boolean): void {
    this.input.setEnabled(enabled);

    if (!enabled) {
      this.clearMoveTarget();
      this.stopLocomotionVectors();

      if (!this.isSitting && !this.activeEmote) {
        this.setMovementState(MovementState.Idle);
      }
    }
  }

  public setMoveTarget(target: THREE.Vector3): void {
    if (this.isSitting || this.activeEmote) {
      return;
    }

    this.moveTarget = target.clone();
    this.blockedTime = 0;

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
    this.blockedTime = 0;
  }

  public playEmote(emoteId: string): void {
    if (this.isSitting) {
      return;
    }

    if (this.emoteTimer) {
      clearTimeout(this.emoteTimer);
    }

    this.clearMoveTarget();
    this.stopLocomotionVectors();
    this.setMovementState(MovementState.Idle);
    this.activeEmote = emoteId;

    if (this.characterModel.isLoaded) {
      const animationName = this.resolveEmoteAnimation(emoteId);

      if (animationName) {
        this.characterModel.play(animationName, 0.1);
      } else {
        console.warn(
          `No hay animación disponible para el emote "${emoteId}".`,
        );
      }
    }

    this.emoteTimer = setTimeout(() => {
      this.activeEmote = null;
      this.emoteTimer = null;

      if (!this.isSitting) {
        this.setMovementState(MovementState.Idle, true);
      }
    }, 3000);
  }

  public enterSitState(
    sitPosition: THREE.Vector3,
    sitRotation: number,
  ): void {
    this.isSitting = true;
    this.clearMoveTarget();
    this.stopLocomotionVectors();

    this.object.position.copy(sitPosition);
    this.object.position.y = 0;

    this.rotationEuler.set(0, sitRotation, 0);
    this.targetQuaternion.setFromEuler(this.rotationEuler);
    this.object.quaternion.copy(this.targetQuaternion);

    this.updateCollider(this.object.position);
    this.setMovementState(MovementState.Sitting);
  }

  public exitSitState(): void {
    this.isSitting = false;
    this.setMovementState(MovementState.Idle);
  }

  public update(deltaTime: number): void {
    this.characterModel.update(deltaTime);

    if (this.isSitting || this.activeEmote) {
      return;
    }

    const input = this.input.getMovementInput();

    if (input.lengthSq() > 0) {
      this.clearMoveTarget();
      this.setMovementDirectionFromInput(input);
    } else if (this.moveTarget) {
      this.desiredMovementDirection
        .copy(this.moveTarget)
        .sub(this.object.position);
      this.desiredMovementDirection.y = 0;

      if (
        this.desiredMovementDirection.length()
        < CLICK_TARGET_REACHED_DISTANCE
      ) {
        this.clearMoveTarget();
        this.stopLocomotionVectors();
        this.setMovementState(MovementState.Idle);
        return;
      }

      this.desiredMovementDirection.normalize();
    } else {
      this.stopLocomotionVectors();
      this.setMovementState(MovementState.Idle);
      return;
    }

    this.setMovementState(MovementState.Walking);

    // Preserve the current gait phase while steering. Translation follows the
    // gradually rotated body instead of snapping to a new direction mid-step.
    this.rotateTowardsMovement(deltaTime);
    this.movementDirection
      .set(0, 0, 1)
      .applyQuaternion(this.object.quaternion);
    this.movementDirection.y = 0;
    this.movementDirection.normalize();

    this.previousPosition.copy(this.object.position);
    this.object.position.x += this.movementDirection.x * this.speed * deltaTime;
    this.object.position.z += this.movementDirection.z * this.speed * deltaTime;

    this.object.position.x = THREE.MathUtils.clamp(
      this.object.position.x,
      -this.mapLimit,
      this.mapLimit,
    );
    this.object.position.z = THREE.MathUtils.clamp(
      this.object.position.z,
      -this.mapLimit,
      this.mapLimit,
    );

    // Keep the planted foot fixed in world space. During turns this makes the
    // body pivot around the support leg instead of dragging both feet sideways.
    this.applyWalkingFootLock();
    this.updateCollider(this.object.position);

    const hasCollision = this.colliders.some(
      (collider) => this.playerCollider.intersectsBox(collider),
    );

    if (hasCollision) {
      this.object.position.copy(this.previousPosition);
      this.clearFootLock();
      this.updateCollider(this.object.position);

      if (this.moveTarget) {
        this.blockedTime += deltaTime;

        if (this.blockedTime >= CLICK_TARGET_BLOCK_TIMEOUT) {
          this.clearMoveTarget();
          this.stopLocomotionVectors();
          this.setMovementState(MovementState.Idle);
        }
      }

      return;
    }

    this.blockedTime = 0;
  }

  public dispose(): void {
    if (this.emoteTimer) {
      clearTimeout(this.emoteTimer);
      this.emoteTimer = null;
    }

    this.input.dispose();
    this.characterModel.dispose();
    this.object.removeFromParent();
    this.activeEmote = null;
    this.clearMoveTarget();
  }

  private setMovementDirectionFromInput(input: THREE.Vector2): void {
    this.camera.getWorldDirection(this.cameraForward);
    this.cameraForward.y = 0;
    this.cameraForward.normalize();

    this.cameraRight
      .crossVectors(this.cameraForward, this.camera.up)
      .normalize();

    this.desiredMovementDirection
      .set(0, 0, 0)
      .addScaledVector(this.cameraForward, input.y)
      .addScaledVector(this.cameraRight, input.x)
      .normalize();
  }

  private rotateTowardsMovement(deltaTime: number): void {
    const targetRotation = Math.atan2(
      this.desiredMovementDirection.x,
      this.desiredMovementDirection.z,
    );

    this.rotationEuler.set(0, targetRotation, 0);
    this.targetQuaternion.setFromEuler(this.rotationEuler);

    const turnBlend = 1 - Math.exp(-deltaTime / TURN_RESPONSE_TIME);
    this.object.quaternion.slerp(this.targetQuaternion, turnBlend);
  }

  private applyWalkingFootLock(): void {
    const supportFoot = this.characterModel.getWalkingSupportFootWorldPosition(
      this.supportFootPosition,
    );

    if (!supportFoot) {
      this.clearFootLock();
      return;
    }

    if (supportFoot !== this.supportFoot) {
      this.supportFoot = supportFoot;
      this.supportFootAnchor.copy(this.supportFootPosition);
      return;
    }

    this.supportFootCorrection
      .copy(this.supportFootAnchor)
      .sub(this.supportFootPosition);
    this.supportFootCorrection.y = 0;

    // Bound one-frame correction so a pathological frame cannot teleport the player.
    if (this.supportFootCorrection.lengthSq() > 0.15 * 0.15) {
      this.supportFootCorrection.setLength(0.15);
    }

    this.object.position.add(this.supportFootCorrection);
    this.object.updateWorldMatrix(true, true);
  }

  private clearFootLock(): void {
    this.supportFoot = null;
    this.supportFootAnchor.set(0, 0, 0);
    this.supportFootPosition.set(0, 0, 0);
    this.supportFootCorrection.set(0, 0, 0);
  }

  private stopLocomotionVectors(): void {
    this.desiredMovementDirection.set(0, 0, 0);
    this.movementDirection.set(0, 0, 0);
    this.clearFootLock();
  }

  private syncAnimationAfterLoad(): void {
    if (!this.characterModel.isLoaded) {
      return;
    }

    if (this.activeEmote) {
      const animationName = this.resolveEmoteAnimation(this.activeEmote);

      if (animationName) {
        this.characterModel.play(animationName, 0);
      }

      return;
    }

    this.setMovementState(this.movementState, true);
  }

  private setMovementState(
    state: MovementStateValue,
    forceAnimation = false,
  ): void {
    if (this.movementState === state && !forceAnimation) {
      return;
    }

    this.movementState = state;
    this.characterModel.setMovementState(state);
  }

  private resolveEmoteAnimation(emoteId: string): string | null {
    if (this.characterModel.hasAnimation(emoteId)) {
      return emoteId;
    }

    if (this.characterModel.hasAnimation("wave")) {
      console.warn(
        `El emote "${emoteId}" no existe; se usará "wave" como fallback.`,
      );
      return "wave";
    }

    return null;
  }

  private updateCollider(position: THREE.Vector3): void {
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
