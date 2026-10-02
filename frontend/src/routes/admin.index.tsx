import { createFileRoute } from "@tanstack/react-router";
import { useQuery } from "@tanstack/react-query";
import { Users, Package, ShoppingCart, DollarSign } from "lucide-react";
import { AppShell } from "@/components/layout/AppShell";
import { Skeleton } from "@/components/ui/skeleton";
import { Badge } from "@/components/ui/badge";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { RequireAuth } from "@/lib/auth/RequireAuth";
import { adminApi } from "@/lib/api/admin";
import { formatCurrency, formatDate } from "@/lib/format";

export const Route = createFileRoute("/admin/")({
  component: () => (
    <RequireAuth roles={["admin"]}>
      <AdminDashboard />
    </RequireAuth>
  ),
});

function AdminDashboard() {
  const stats = useQuery({ queryKey: ["admin-stats"], queryFn: () => adminApi.dashboard() });

  const cards = [
    { label: "Total users", value: stats.data?.total_users ?? "—", icon: Users },
    { label: "Total orders", value: stats.data?.total_orders ?? "—", icon: ShoppingCart },
    { label: "Total products", value: stats.data?.total_products ?? "—", icon: Package },
    { label: "Revenue", value: stats.data ? formatCurrency(stats.data.revenue) : "—", icon: DollarSign },
  ];

  return (
    <AppShell>
      <div className="mx-auto max-w-7xl px-4 py-10 sm:px-6 lg:px-8">
        <h1 className="font-display text-3xl font-semibold">Admin dashboard</h1>
        <p className="mt-1 text-sm text-muted-foreground">Platform health at a glance.</p>

        <div className="mt-8 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {cards.map((c) => (
            <div key={c.label} className="rounded-2xl border border-border/60 bg-card p-5">
              <c.icon className="h-5 w-5 text-accent" />
              <div className="mt-4 text-xs uppercase tracking-wider text-muted-foreground">{c.label}</div>
              {stats.isLoading ? (
                <Skeleton className="mt-1 h-7 w-24" />
              ) : (
                <div className="mt-1 text-2xl font-semibold">{c.value}</div>
              )}
            </div>
          ))}
        </div>

        <section className="mt-12 rounded-2xl border border-border/60 bg-card">
          <div className="border-b border-border/60 p-5">
            <h2 className="font-display text-lg font-semibold">Recent orders</h2>
          </div>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Order</TableHead>
                <TableHead>Date</TableHead>
                <TableHead>Status</TableHead>
                <TableHead className="text-right">Total</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {stats.data?.recent_orders?.map((o) => (
                <TableRow key={o.id}>
                  <TableCell className="font-mono text-xs">#{o.id.slice(0, 8)}</TableCell>
                  <TableCell>{formatDate(o.created_at)}</TableCell>
                  <TableCell><Badge variant="outline" className="capitalize">{o.order_status}</Badge></TableCell>
                  <TableCell className="text-right">{formatCurrency(o.total_amount)}</TableCell>
                </TableRow>
              ))}
              {!stats.isLoading && !stats.data?.recent_orders?.length && (
                <TableRow>
                  <TableCell colSpan={4} className="py-10 text-center text-sm text-muted-foreground">
                    No orders yet.
                  </TableCell>
                </TableRow>
              )}
            </TableBody>
          </Table>
        </section>
      </div>
    </AppShell>
  );
}
