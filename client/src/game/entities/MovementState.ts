export const MovementState = {
  Idle: "idle",
  Walking: "walk",
  Sitting: "sit",
} as const;

export type MovementState =
  (typeof MovementState)[keyof typeof MovementState];
