import { createFileRoute } from "@tanstack/react-router";
import { useQuery } from "@tanstack/react-query";
import { AppShell } from "@/components/layout/AppShell";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { RequireAuth } from "@/lib/auth/RequireAuth";
import { ordersApi } from "@/lib/api/orders";
import { formatCurrency, formatDateTime } from "@/lib/format";

export const Route = createFileRoute("/orders/$id")({
  component: () => (
    <RequireAuth>
      <OrderDetail />
    </RequireAuth>
  ),
});

function OrderDetail() {
  const { id } = Route.useParams();
  const order = useQuery({ queryKey: ["order", id], queryFn: () => ordersApi.get(id) });

  if (order.isLoading) {
    return (
      <AppShell>
        <div className="mx-auto max-w-3xl px-4 py-10">
          <Skeleton className="h-64 w-full rounded-2xl" />
        </div>
      </AppShell>
    );
  }
  if (!order.data) {
    return (
      <AppShell>
        <div className="mx-auto max-w-2xl px-4 py-20 text-center">
          <h1 className="text-2xl font-semibold">Order not found</h1>
        </div>
      </AppShell>
    );
  }
  const o = order.data;

  return (
    <AppShell>
      <div className="mx-auto max-w-3xl px-4 py-10 sm:px-6 lg:px-8">
        <div className="flex items-start justify-between gap-4">
          <div>
            <p className="text-xs text-muted-foreground">Order</p>
            <h1 className="font-display text-2xl font-semibold">#{o.id.slice(0, 8)}</h1>
            <p className="mt-1 text-sm text-muted-foreground">{formatDateTime(o.created_at)}</p>
          </div>
          <div className="flex flex-col items-end gap-2">
            <Badge>{o.order_status}</Badge>
            <Badge variant="outline">Payment: {o.payment_status}</Badge>
          </div>
        </div>

        <section className="mt-8 rounded-2xl border border-border/60 bg-card p-6">
          <h2 className="font-display text-lg font-semibold">Items</h2>
          <ul className="mt-4 divide-y divide-border/60">
            {o.items.map((i) => (
              <li key={i.id} className="flex items-center justify-between py-3">
                <div>
                  <div className="font-medium">{i.product_name}</div>
                  <div className="text-xs text-muted-foreground">Qty {i.quantity}</div>
                </div>
                <span>{formatCurrency(i.price * i.quantity)}</span>
              </li>
            ))}
          </ul>
          <div className="mt-4 flex justify-between border-t border-border/60 pt-4 text-base font-semibold">
            <span>Total</span>
            <span>{formatCurrency(o.total_amount)}</span>
          </div>
        </section>

        <section className="mt-6 rounded-2xl border border-border/60 bg-card p-6">
          <h2 className="font-display text-lg font-semibold">Shipping</h2>
          <p className="mt-2 text-sm text-muted-foreground whitespace-pre-line">{o.shipping_address}</p>
        </section>
      </div>
    </AppShell>
  );
}
