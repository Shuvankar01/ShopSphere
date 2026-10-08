import { createFileRoute, Link } from "@tanstack/react-router";
import { useQuery } from "@tanstack/react-query";
import { Package, ShoppingBag, User as UserIcon, Store, Heart, Boxes } from "lucide-react";
import { AppShell } from "@/components/layout/AppShell";
import { Skeleton } from "@/components/ui/skeleton";
import { RequireAuth } from "@/lib/auth/RequireAuth";
import { useAuth } from "@/lib/auth/AuthContext";
import { ordersApi } from "@/lib/api/orders";
import { formatCurrency, formatDate } from "@/lib/format";

export const Route = createFileRoute("/dashboard")({
  component: () => (
    <RequireAuth>
      <Dashboard />
    </RequireAuth>
  ),
});

function Dashboard() {
  const { user } = useAuth();
  const orders = useQuery({ queryKey: ["orders"], queryFn: () => ordersApi.list() });

  const stats = [
    { label: "Orders", value: orders.data?.length ?? "—", icon: Package, to: "/orders" },
    { label: "Wishlist", value: "Saved", icon: Heart, to: "/wishlist" },
    { label: "Profile", value: user?.full_name ?? "—", icon: UserIcon, to: "/profile" },
    { label: "Shop", value: "Browse", icon: ShoppingBag, to: "/products" },
    ...(user?.role === "seller"
      ? [
          { label: "Seller hub", value: "Manage", icon: Store, to: "/seller/products" },
          { label: "Inventory", value: "Stock", icon: Boxes, to: "/seller/inventory" },
        ]
      : []),
  ];

  return (
    <AppShell>
      <div className="mx-auto max-w-6xl px-4 py-10 sm:px-6 lg:px-8">
        <h1 className="font-display text-3xl font-semibold">
          Welcome back, {user?.full_name.split(" ")[0]}
        </h1>
        <p className="mt-1 text-sm text-muted-foreground">Here's a snapshot of your account.</p>

        <div className="mt-8 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {stats.map((s) => (
            <Link
              key={s.label}
              to={s.to}
              className="rounded-2xl border border-border/60 bg-card p-5 transition-colors hover:border-accent/60"
            >
              <s.icon className="h-5 w-5 text-accent" />
              <div className="mt-4 text-xs uppercase tracking-wider text-muted-foreground">
                {s.label}
              </div>
              <div className="mt-1 truncate text-lg font-semibold">{s.value}</div>
            </Link>
          ))}
        </div>

        <section className="mt-12">
          <h2 className="font-display text-xl font-semibold">Recent orders</h2>
          {orders.isLoading ? (
            <Skeleton className="mt-4 h-32 w-full rounded-2xl" />
          ) : !orders.data?.length ? (
            <p className="mt-4 text-sm text-muted-foreground">No orders yet.</p>
          ) : (
            <div className="mt-4 space-y-2">
              {orders.data.slice(0, 5).map((o) => (
                <Link
                  key={o.id}
                  to="/orders/$id"
                  params={{ id: o.id }}
                  className="flex items-center justify-between rounded-xl border border-border/60 bg-card p-4 hover:border-accent/60"
                >
                  <div>
                    <div className="text-sm font-medium">#{o.id.slice(0, 8)}</div>
                    <div className="text-xs text-muted-foreground">{formatDate(o.created_at)}</div>
                  </div>
                  <div className="flex items-center gap-3 text-sm">
                    <span className="capitalize text-muted-foreground">{o.order_status}</span>
                    <span className="font-semibold">{formatCurrency(o.total_amount)}</span>
                  </div>
                </Link>
              ))}
            </div>
          )}
        </section>
      </div>
    </AppShell>
  );
}
