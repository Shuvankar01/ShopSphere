import { createFileRoute, Link } from "@tanstack/react-router";
import { useQuery } from "@tanstack/react-query";
import { AppShell } from "@/components/layout/AppShell";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { Button } from "@/components/ui/button";
import { RequireAuth } from "@/lib/auth/RequireAuth";
import { ordersApi } from "@/lib/api/orders";
import { formatCurrency, formatDate } from "@/lib/format";
import type { OrderStatus } from "@/lib/types";

const statusColor: Record<OrderStatus, string> = {
  pending: "bg-yellow-500/15 text-yellow-700 dark:text-yellow-300",
  confirmed: "bg-blue-500/15 text-blue-700 dark:text-blue-300",
  processing: "bg-sky-500/15 text-sky-700 dark:text-sky-300",
  packed: "bg-indigo-500/15 text-indigo-700 dark:text-indigo-300",
  shipped: "bg-purple-500/15 text-purple-700 dark:text-purple-300",
  out_for_delivery: "bg-teal-500/15 text-teal-700 dark:text-teal-300",
  delivered: "bg-accent/15 text-accent-foreground",
  cancelled: "bg-destructive/15 text-destructive",
};

export const Route = createFileRoute("/orders")({
  component: () => (
    <RequireAuth>
      <OrdersPage />
    </RequireAuth>
  ),
});

function OrdersPage() {
  const orders = useQuery({ queryKey: ["orders"], queryFn: () => ordersApi.list() });

  return (
    <AppShell>
      <div className="mx-auto max-w-5xl px-4 py-10 sm:px-6 lg:px-8">
        <h1 className="font-display text-3xl font-semibold">Orders</h1>

        {orders.isLoading ? (
          <Skeleton className="mt-8 h-40 w-full rounded-2xl" />
        ) : !orders.data?.length ? (
          <div className="mt-12 rounded-2xl border border-dashed border-border bg-muted/20 p-12 text-center">
            <p className="text-muted-foreground">You haven't placed any orders yet.</p>
            <Link to="/products"><Button className="mt-6">Start shopping</Button></Link>
          </div>
        ) : (
          <div className="mt-8 space-y-3">
            {orders.data.map((o) => (
              <Link
                key={o.id}
                to="/orders/$id"
                params={{ id: o.id }}
                className="flex flex-col gap-3 rounded-2xl border border-border/60 bg-card p-5 transition-colors hover:border-accent/60 sm:flex-row sm:items-center sm:justify-between"
              >
                <div>
                  <div className="text-xs text-muted-foreground">Order #{o.id.slice(0, 8)}</div>
                  <div className="mt-1 font-medium">{formatDate(o.created_at)}</div>
                  <div className="mt-1 text-sm text-muted-foreground">
                    {o.items.length} item{o.items.length === 1 ? "" : "s"}
                  </div>
                </div>
                <div className="flex items-center gap-4">
                  <Badge className={statusColor[o.order_status]}>{o.order_status}</Badge>
                  <span className="text-lg font-semibold">{formatCurrency(o.total_amount)}</span>
                </div>
              </Link>
            ))}
          </div>
        )}
      </div>
    </AppShell>
  );
}
