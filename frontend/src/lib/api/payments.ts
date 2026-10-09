import { api } from "./client";
import { num } from "./normalize";
import type { PaymentTransaction } from "@/lib/types";

export function mapPaymentTransaction(p: any): PaymentTransaction {
  return {
    ...p,
    amount: num(p.amount) ?? 0,
  };
}

export const paymentsApi = {
  create: (data: { order_id: string; payment_method: string }) =>
    api
      .post<{ transaction_id: string; status: string; provider?: string; amount?: string | number; currency?: string; redirect_url?: string }>(
        "/api/payment/create",
        data,
      ),
  complete: (transactionId: string, result: "success" | "failure" | "cancel") =>
    api.post(`/api/payment/${transactionId}/complete`, { result }),
  webhook: (event: { transaction_id: string; event: string; amount?: number | string }) =>
    api.post("/api/payment/webhook", event),
};
