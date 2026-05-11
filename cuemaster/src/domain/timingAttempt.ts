export type TimingAttempt = {
  id: string;
  playbookId: string;
  roleId: string;
  lineId: string;
  createdAt: number;
  hesitationMs: number;
  deliveryMs: number;
  targetHesitationMs: number;
  targetDeliveryMs: number;
  hesitationLabel: "sharp" | "close" | "late";
  deliveryLabel: "fast" | "close" | "slow";
  detectionMode: "energy";
};
