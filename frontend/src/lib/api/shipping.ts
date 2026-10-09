import { api } from "./client";
import { num } from "./normalize";
import type { ShippingMethod } from "@/lib/types";

function mapMethod(m: any): ShippingMethod {
  return {
    ...m,
    charge: num(m.charge) ?? 0,
    estimated_days_min: m.estimated_days_min ?? 0,
    estimated_days_max: m.estimated_days_max ?? 0,
  };
}

export const shippingApi = {
  list: () => api.get<ShippingMethod[]>("/api/shipping/methods").then((list) => list.map(mapMethod)),
};
