import { createFileRoute, Link } from "@tanstack/react-router";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Minus, Plus, Trash2, ShoppingBag, Tag, X } from "lucide-react";
import { useState } from "react";
import { toast } from "sonner";
import { AppShell } from "@/components/layout/AppShell";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { RequireAuth } from "@/lib/auth/RequireAuth";
import { useCart } from "@/hooks/useCart";
import { cartApi } from "@/lib/api/cart";
import { formatCurrency } from "@/lib/format";

export const Route = createFileRoute("/cart")({
  component: () => (
    <RequireAuth>
      <CartPage />
    </RequireAuth>
  ),
});

function CartPage() {
  const cart = useCart();
  const qc = useQueryClient();
  const [couponInput, setCouponInput] = useState("");

  const invalidate = () => {
    qc.invalidateQueries({ queryKey: ["cart"] });
    qc.invalidateQueries({ queryKey: ["products"] });
  };

  const updateQty = useMutation({
    mutationFn: ({ id, qty }: { id: string; qty: number }) => cartApi.update(id, qty),
    onSuccess: invalidate,
    onError: (e: Error) => toast.error(e.message),
  });
  const remove = useMutation({
    mutationFn: (id: string) => cartApi.remove(id),
    onSuccess: invalidate,
    onError: (e: Error) => toast.error(e.message),
  });
  const applyCoupon = useMutation({
    mutationFn: () => cartApi.applyCoupon(couponInput.trim()),
    onSuccess: () => {
      toast.success("Coupon applied");
      setCouponInput("");
      invalidate();
    },
    onError: (e: Error) => toast.error(e.message),
  });
  const removeCoupon = useMutation({
    mutationFn: () => cartApi.removeCoupon(),
    onSuccess: invalidate,
    onError: (e: Error) => toast.error(e.message),
  });

  return (
    <AppShell>
      <div className="mx-auto max-w-5xl px-4 py-10 sm:px-6 lg:px-8">
        <h1 className="font-display text-3xl font-semibold">Your cart</h1>

        {cart.isLoading ? (
          <Skeleton className="mt-8 h-40 w-full rounded-2xl" />
        ) : !cart.data || cart.data.items.length === 0 ? (
          <div className="mt-12 rounded-2xl border border-dashed border-border bg-muted/20 p-12 text-center">
            <ShoppingBag className="mx-auto h-10 w-10 text-muted-foreground" />
            <p className="mt-4 text-muted-foreground">Your cart is empty.</p>
            <Link to="/products">
              <Button className="mt-6">Continue shopping</Button>
            </Link>
          </div>
        ) : (
          <div className="mt-8 grid gap-8 lg:grid-cols-[1fr_360px]">
            <div className="space-y-3">
              {cart.data.items.map((item) => {
                const p = item.product;
                const price = p.discount_price ?? p.price;
                return (
                  <div
                    key={item.id}
                    className="flex gap-4 rounded-2xl border border-border/60 bg-card p-4"
                  >
                    <div className="h-24 w-24 overflow-hidden rounded-xl bg-muted">
                      {(p.image_url || p.images?.[0]?.url) && (
                        <img
                          src={p.image_url || p.images?.[0]?.url}
                          alt={p.name}
                          className="h-full w-full object-cover"
                        />
                      )}
                    </div>
                    <div className="flex flex-1 flex-col">
                      <Link
                        to="/products/$id"
                        params={{ id: p.id }}
                        className="text-sm font-medium hover:underline"
                      >
                        {p.name}
                      </Link>
                      <div className="mt-1 text-xs text-muted-foreground">
                        {formatCurrency(price)} each
                      </div>
                      <div className="mt-auto flex items-center justify-between">
                        <div className="flex items-center rounded-md border border-input">
                          <button
                            className="px-2 py-1.5 hover:bg-muted disabled:opacity-50"
                            disabled={updateQty.isPending}
                            onClick={() =>
                              updateQty.mutate({ id: p.id, qty: Math.max(1, item.quantity - 1) })
                            }
                          >
                            <Minus className="h-3 w-3" />
                          </button>
                          <span className="w-8 text-center text-sm">{item.quantity}</span>
                          <button
                            className="px-2 py-1.5 hover:bg-muted disabled:opacity-50"
                            disabled={updateQty.isPending}
                            onClick={() => updateQty.mutate({ id: p.id, qty: item.quantity + 1 })}
                          >
                            <Plus className="h-3 w-3" />
                          </button>
                        </div>
                        <div className="flex items-center gap-3">
                          <span className="font-semibold">
                            {formatCurrency(price * item.quantity)}
                          </span>
                          <Button variant="ghost" size="icon" onClick={() => remove.mutate(p.id)}>
                            <Trash2 className="h-4 w-4" />
                          </Button>
                        </div>
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>

            <aside className="h-fit space-y-5 rounded-2xl border border-border/60 bg-card p-6">
              <h2 className="font-display text-lg font-semibold">Order summary</h2>

              {/* Coupon */}
              {cart.data.coupon_code ? (
                <div className="flex items-center justify-between rounded-xl border border-accent/30 bg-accent/10 px-3 py-2.5 text-sm">
                  <span className="flex items-center gap-2 font-medium text-accent">
                    <Tag className="h-4 w-4" /> {cart.data.coupon_code}
                  </span>
                  <Button
                    variant="ghost"
                    size="icon"
                    className="h-7 w-7"
                    onClick={() => removeCoupon.mutate()}
                    disabled={removeCoupon.isPending}
                    aria-label="Remove coupon"
                  >
                    <X className="h-4 w-4" />
                  </Button>
                </div>
              ) : (
                <div>
                  <Label className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                    Coupon code
                  </Label>
                  <div className="mt-2 flex gap-2">
                    <Input
                      value={couponInput}
                      onChange={(e) => setCouponInput(e.target.value)}
                      placeholder="e.g. WELCOME10"
                      className="uppercase"
                    />
                    <Button
                      variant="outline"
                      onClick={() => applyCoupon.mutate()}
                      disabled={applyCoupon.isPending || !couponInput.trim()}
                    >
                      Apply
                    </Button>
                  </div>
                </div>
              )}

              <div className="space-y-2 text-sm">
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Subtotal</span>
                  <span>{formatCurrency(cart.data.subtotal)}</span>
                </div>
                {(cart.data.discount_amount ?? 0) > 0 && (
                  <div className="flex justify-between text-accent">
                    <span>Discount</span>
                    <span>−{formatCurrency(cart.data.discount_amount)}</span>
                  </div>
                )}
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Shipping</span>
                  <span className="text-accent">Calculated at checkout</span>
                </div>
                <div className="mt-4 flex justify-between border-t border-border/60 pt-4 text-base font-semibold">
                  <span>Total</span>
                  <span>{formatCurrency(cart.data.total)}</span>
                </div>
              </div>
              <Link to="/checkout">
                <Button className="mt-2 w-full" size="lg">
                  Checkout
                </Button>
              </Link>
            </aside>
          </div>
        )}
      </div>
    </AppShell>
  );
}
