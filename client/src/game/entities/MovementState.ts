export const MovementState = {
  Idle: "idle",
  Walking: "walking",
  Sitting: "sitting",
} as const;

export type MovementState =
  (typeof MovementState)[keyof typeof MovementState];
