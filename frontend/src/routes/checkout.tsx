import { createFileRoute, useNavigate } from "@tanstack/react-router";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import type { z } from "zod";
import { AppShell } from "@/components/layout/AppShell";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { RequireAuth } from "@/lib/auth/RequireAuth";
import { useCart } from "@/hooks/useCart";
import { ordersApi } from "@/lib/api/orders";
import { paymentsApi } from "@/lib/api/payments";
import { checkoutSchema } from "@/lib/schemas";
import { formatCurrency } from "@/lib/format";

export const Route = createFileRoute("/checkout")({
  component: () => (
    <RequireAuth>
      <CheckoutPage />
    </RequireAuth>
  ),
});

type FormValues = z.infer<typeof checkoutSchema>;

function CheckoutPage() {
  const cart = useCart();
  const navigate = useNavigate();
  const qc = useQueryClient();
  const {
    register,
    handleSubmit,
    setValue,
    watch,
    formState: { errors },
  } = useForm<FormValues>({
    resolver: zodResolver(checkoutSchema),
    defaultValues: { payment_method: "card" },
  });

  const placeOrder = useMutation({
    mutationFn: async (v: FormValues) => {
      const shipping_address = `${v.full_name}, ${v.address_line}, ${v.city}, ${v.postal_code}, ${v.country}`;
      const order = await ordersApi.create({ shipping_address, payment_method: v.payment_method });
      await paymentsApi.create({ order_id: order.id, payment_method: v.payment_method });
      return order;
    },
    onSuccess: (order) => {
      qc.invalidateQueries({ queryKey: ["cart"] });
      qc.invalidateQueries({ queryKey: ["orders"] });
      toast.success("Order placed");
      navigate({ to: "/orders/$id", params: { id: order.id } });
    },
    onError: (e: Error) => toast.error(e.message),
  });

  if (!cart.data || cart.data.items.length === 0) {
    return (
      <AppShell>
        <div className="mx-auto max-w-2xl px-4 py-20 text-center">
          <h1 className="text-2xl font-semibold">Your cart is empty</h1>
          <p className="mt-2 text-muted-foreground">Add items before checking out.</p>
        </div>
      </AppShell>
    );
  }

  return (
    <AppShell>
      <div className="mx-auto max-w-5xl px-4 py-10 sm:px-6 lg:px-8">
        <h1 className="font-display text-3xl font-semibold">Checkout</h1>
        <form
          onSubmit={handleSubmit((v) => placeOrder.mutate(v))}
          className="mt-8 grid gap-8 lg:grid-cols-[1fr_360px]"
        >
          <div className="space-y-6 rounded-2xl border border-border/60 bg-card p-6">
            <h2 className="font-display text-lg font-semibold">Shipping address</h2>
            <div className="grid gap-4 sm:grid-cols-2">
              <div className="sm:col-span-2 space-y-1.5">
                <Label>Full name</Label>
                <Input {...register("full_name")} />
                {errors.full_name && (
                  <p className="text-xs text-destructive">{errors.full_name.message}</p>
                )}
              </div>
              <div className="sm:col-span-2 space-y-1.5">
                <Label>Address</Label>
                <Input {...register("address_line")} />
                {errors.address_line && (
                  <p className="text-xs text-destructive">{errors.address_line.message}</p>
                )}
              </div>
              <div className="space-y-1.5">
                <Label>City</Label>
                <Input {...register("city")} />
                {errors.city && <p className="text-xs text-destructive">{errors.city.message}</p>}
              </div>
              <div className="space-y-1.5">
                <Label>Postal code</Label>
                <Input {...register("postal_code")} />
              </div>
              <div className="sm:col-span-2 space-y-1.5">
                <Label>Country</Label>
                <Input {...register("country")} />
              </div>
            </div>

            <div className="space-y-1.5">
              <Label>Payment method</Label>
              <Select
                value={watch("payment_method")}
                onValueChange={(v) => setValue("payment_method", v as FormValues["payment_method"])}
              >
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="card">Credit / debit card</SelectItem>
                  <SelectItem value="paypal">PayPal</SelectItem>
                  <SelectItem value="cod">Cash on delivery</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>

          <aside className="h-fit rounded-2xl border border-border/60 bg-card p-6">
            <h2 className="font-display text-lg font-semibold">Order</h2>
            <div className="mt-4 space-y-2 text-sm">
              {cart.data.items.map((i) => (
                <div key={i.id} className="flex justify-between">
                  <span className="text-muted-foreground">
                    {i.product.name} × {i.quantity}
                  </span>
                  <span>
                    {formatCurrency((i.product.discount_price ?? i.product.price) * i.quantity)}
                  </span>
                </div>
              ))}
              <div className="mt-4 flex justify-between border-t border-border/60 pt-4 text-base font-semibold">
                <span>Total</span>
                <span>{formatCurrency(cart.data.total)}</span>
              </div>
              {(cart.data.discount_amount ?? 0) > 0 && (
                <div className="flex justify-between text-xs text-accent">
                  <span>
                    Coupon {cart.data.coupon_code ? `${cart.data.coupon_code} applied` : "applied"}
                  </span>
                  <span>−{formatCurrency(cart.data.discount_amount)}</span>
                </div>
              )}
            </div>
            <Button type="submit" className="mt-6 w-full" size="lg" disabled={placeOrder.isPending}>
              {placeOrder.isPending ? "Placing order…" : "Place order"}
            </Button>
          </aside>
        </form>
      </div>
    </AppShell>
  );
}
