import fs from "node:fs";
import path from "node:path";
import * as THREE from "three";
import { GLTFLoader } from "three/examples/jsm/loaders/GLTFLoader.js";

const MODEL_PATH = path.resolve("public/models/chatgpt-fox-proxy-v5.glb");
const WALK_REFERENCE_SPEED = 1.385;
const GAMEPLAY_SPEED = 2.2;
const TURN_RESPONSE_TIME = 0.16;
const DT = 1 / 60;
const TEST_DURATION = 3;

function loadGlb(filePath) {
  const bytes = fs.readFileSync(filePath);
  const arrayBuffer = bytes.buffer.slice(
    bytes.byteOffset,
    bytes.byteOffset + bytes.byteLength,
  );

  return new Promise((resolve, reject) => {
    new GLTFLoader().parse(arrayBuffer, "", resolve, reject);
  });
}

function desiredDirection(time, target) {
  if (time < 0.75) {
    return target.set(0, 0, 1);
  }
  if (time < 1.5) {
    return target.set(1, 0, 0);
  }
  if (time < 2.25) {
    return target.set(0, 0, -1);
  }
  return target.set(-1, 0, 0);
}

async function simulate({ useFootLock }) {
  const gltf = await loadGlb(MODEL_PATH);
  const model = gltf.scene;
  model.scale.setScalar(0.32);

  const player = new THREE.Group();
  player.add(model);

  const walkingClip = THREE.AnimationClip.findByName(gltf.animations, "walking");
  if (!walkingClip) {
    throw new Error("walking clip is missing");
  }

  const leftFoot = model.getObjectByName("MDL_FOOT_L");
  const rightFoot = model.getObjectByName("MDL_FOOT_R");
  if (!leftFoot || !rightFoot) {
    throw new Error("foot nodes are missing");
  }

  const mixer = new THREE.AnimationMixer(model);
  const action = mixer.clipAction(walkingClip);
  action.setLoop(THREE.LoopRepeat, Infinity);
  action.setEffectiveTimeScale(GAMEPLAY_SPEED / WALK_REFERENCE_SPEED);
  action.play();

  const desired = new THREE.Vector3();
  const forward = new THREE.Vector3();
  const rotationEuler = new THREE.Euler();
  const targetQuaternion = new THREE.Quaternion();
  const footPosition = new THREE.Vector3();
  const footAnchor = new THREE.Vector3();
  const correction = new THREE.Vector3();

  let supportFoot = null;
  let maximumSupportDrift = 0;
  let accumulatedSupportDrift = 0;
  let supportSamples = 0;
  let supportSwitches = 0;
  let maximumCorrection = 0;
  let totalDistance = 0;
  const previousPosition = new THREE.Vector3();

  for (let time = 0; time < TEST_DURATION; time += DT) {
    mixer.update(DT);
    desiredDirection(time, desired);

    const targetRotation = Math.atan2(desired.x, desired.z);
    rotationEuler.set(0, targetRotation, 0);
    targetQuaternion.setFromEuler(rotationEuler);
    const turnBlend = 1 - Math.exp(-DT / TURN_RESPONSE_TIME);
    player.quaternion.slerp(targetQuaternion, turnBlend);

    forward.set(0, 0, 1).applyQuaternion(player.quaternion);
    forward.y = 0;
    forward.normalize();

    previousPosition.copy(player.position);
    player.position.addScaledVector(forward, GAMEPLAY_SPEED * DT);
    totalDistance += player.position.distanceTo(previousPosition);
    player.updateWorldMatrix(true, true);

    const normalizedPhase =
      (((action.time % walkingClip.duration) + walkingClip.duration)
        % walkingClip.duration)
      / walkingClip.duration;
    const currentSupport = normalizedPhase < 0.5 ? "left" : "right";
    const foot = currentSupport === "left" ? leftFoot : rightFoot;
    foot.getWorldPosition(footPosition);

    if (currentSupport !== supportFoot) {
      supportFoot = currentSupport;
      footAnchor.copy(footPosition);
      supportSwitches += 1;
      continue;
    }

    if (useFootLock) {
      correction.copy(footAnchor).sub(footPosition);
      correction.y = 0;
      if (correction.lengthSq() > 0.15 * 0.15) {
        correction.setLength(0.15);
      }
      maximumCorrection = Math.max(maximumCorrection, correction.length());
      player.position.add(correction);
      player.updateWorldMatrix(true, true);
      foot.getWorldPosition(footPosition);
    }

    const drift = Math.hypot(
      footPosition.x - footAnchor.x,
      footPosition.z - footAnchor.z,
    );
    maximumSupportDrift = Math.max(maximumSupportDrift, drift);
    accumulatedSupportDrift += drift;
    supportSamples += 1;
  }

  return {
    useFootLock,
    walkingClipDuration: walkingClip.duration,
    walkingTimeScale: GAMEPLAY_SPEED / WALK_REFERENCE_SPEED,
    effectiveCycleDuration:
      walkingClip.duration / (GAMEPLAY_SPEED / WALK_REFERENCE_SPEED),
    gameplaySpeed: GAMEPLAY_SPEED,
    totalDistance,
    supportSwitches,
    maximumSupportDrift,
    meanSupportDrift: accumulatedSupportDrift / supportSamples,
    maximumCorrection,
    finalPosition: player.position.toArray(),
  };
}

const withoutFootLock = await simulate({ useFootLock: false });
const withFootLock = await simulate({ useFootLock: true });

const evidence = { withoutFootLock, withFootLock };

if (withFootLock.maximumSupportDrift > 0.015) {
  throw new Error(
    `Foot locking drift is too large: ${withFootLock.maximumSupportDrift}`,
  );
}
if (withFootLock.maximumSupportDrift >= withoutFootLock.maximumSupportDrift * 0.15) {
  throw new Error("Foot locking did not reduce planted-foot drift enough");
}
if (Math.abs(withFootLock.walkingClipDuration - 13 / 24) > 0.001) {
  throw new Error(
    `Unexpected exported walking duration: ${withFootLock.walkingClipDuration}`,
  );
}

const outputPath = path.resolve(
  "../assets/concepts/chatgpt-fox/blender/proxy-v5-foot-lock-runtime-validation.json",
);
fs.writeFileSync(
  outputPath,
  `${JSON.stringify({
    stage: "proxy_v5_fullbody_walk_and_world_foot_lock_validated",
    model: path.relative(path.resolve(".."), MODEL_PATH).replaceAll("\\", "/"),
    calibration: {
      exportedReferenceSpeed: WALK_REFERENCE_SPEED,
      gameplaySpeed: GAMEPLAY_SPEED,
      walkingTimeScale: withFootLock.walkingTimeScale,
      effectiveCycleDuration: withFootLock.effectiveCycleDuration,
      turnResponseTime: TURN_RESPONSE_TIME,
    },
    evidence,
  }, null, 2)}\n`,
  "utf8",
);

console.log(JSON.stringify(evidence, null, 2));
