import fs from "node:fs";
import path from "node:path";
import * as THREE from "three";
import { GLTFLoader } from "three/examples/jsm/loaders/GLTFLoader.js";

const MODEL_PATH = path.resolve("public/models/chatgpt-fox-proxy-v5.glb");
const GAMEPLAY_SPEED = 4;
const DT = 1 / 240;
const TEST_DURATION = 2;

function loadGlb(filePath) {
  const bytes = fs.readFileSync(filePath);
  const arrayBuffer = bytes.buffer.slice(bytes.byteOffset, bytes.byteOffset + bytes.byteLength);
  return new Promise((resolve, reject) => {
    new GLTFLoader().parse(arrayBuffer, "", resolve, reject);
  });
}

const gltf = await loadGlb(MODEL_PATH);
const walkingClip = THREE.AnimationClip.findByName(gltf.animations, "walking");
if (!walkingClip) throw new Error("walking clip is missing");

async function measure(timeScale) {
  const model = gltf.scene.clone(true);
  model.scale.setScalar(0.32);
  const player = new THREE.Group();
  player.add(model);

  const leftFoot = model.getObjectByName("MDL_FOOT_L");
  const rightFoot = model.getObjectByName("MDL_FOOT_R");
  if (!leftFoot || !rightFoot) throw new Error("foot nodes are missing");

  const mixer = new THREE.AnimationMixer(model);
  const action = mixer.clipAction(walkingClip);
  action.setLoop(THREE.LoopRepeat, Infinity);
  action.setEffectiveTimeScale(timeScale);
  action.play();

  const footPosition = new THREE.Vector3();
  const footAnchor = new THREE.Vector3();
  let support = null;
  let samples = 0;
  let squaredDrift = 0;
  let maximumDrift = 0;

  for (let time = 0; time < TEST_DURATION; time += DT) {
    mixer.update(DT);
    player.position.z += GAMEPLAY_SPEED * DT;
    player.updateWorldMatrix(true, true);

    const normalizedPhase = (((action.time % walkingClip.duration) + walkingClip.duration) % walkingClip.duration) / walkingClip.duration;
    const currentSupport = normalizedPhase < 0.5 ? "left" : "right";
    const foot = currentSupport === "left" ? leftFoot : rightFoot;
    foot.getWorldPosition(footPosition);

    if (currentSupport !== support) {
      support = currentSupport;
      footAnchor.copy(footPosition);
      continue;
    }

    const drift = Math.hypot(footPosition.x - footAnchor.x, footPosition.z - footAnchor.z);
    squaredDrift += drift * drift;
    maximumDrift = Math.max(maximumDrift, drift);
    samples += 1;
  }

  return {
    timeScale,
    referenceSpeed: GAMEPLAY_SPEED / timeScale,
    rmsDrift: Math.sqrt(squaredDrift / samples),
    maximumDrift,
  };
}

const coarse = [];
for (let timeScale = 1.8; timeScale <= 3.4; timeScale += 0.02) {
  coarse.push(await measure(timeScale));
}
coarse.sort((left, right) => left.rmsDrift - right.rmsDrift);
const center = coarse[0].timeScale;

const fine = [];
for (let timeScale = center - 0.05; timeScale <= center + 0.05; timeScale += 0.001) {
  fine.push(await measure(timeScale));
}
fine.sort((left, right) => left.rmsDrift - right.rmsDrift);

console.log(JSON.stringify({
  clipDuration: walkingClip.duration,
  gameplaySpeed: GAMEPLAY_SPEED,
  best: fine[0],
  nearby: fine.slice(0, 10),
}, null, 2));
