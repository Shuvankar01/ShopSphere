import { api } from "./client";

export const paymentsApi = {
  create: (data: { order_id: string; payment_method: string }) =>
    api.post<{ transaction_id: string; status: string; redirect_url?: string }>(
      "/api/payment/create",
      data,
    ),
};
