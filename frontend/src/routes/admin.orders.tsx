import { createFileRoute } from "@tanstack/react-router";
import { useQuery } from "@tanstack/react-query";
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

export const Route = createFileRoute("/admin/orders")({
  component: () => (
    <RequireAuth roles={["admin"]}>
      <AdminOrders />
    </RequireAuth>
  ),
});

function AdminOrders() {
  const orders = useQuery({ queryKey: ["admin-orders"], queryFn: () => adminApi.orders() });
  return (
    <AppShell>
      <div className="mx-auto max-w-6xl px-4 py-10 sm:px-6 lg:px-8">
        <h1 className="font-display text-3xl font-semibold">All orders</h1>
        <div className="mt-8 overflow-hidden rounded-2xl border border-border/60 bg-card">
          {orders.isLoading ? (
            <Skeleton className="h-64 w-full" />
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Order</TableHead>
                  <TableHead>Date</TableHead>
                  <TableHead>Items</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead>Payment</TableHead>
                  <TableHead className="text-right">Total</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {orders.data?.map((o) => (
                  <TableRow key={o.id}>
                    <TableCell className="font-mono text-xs">#{o.id.slice(0, 8)}</TableCell>
                    <TableCell>{formatDate(o.created_at)}</TableCell>
                    <TableCell>{o.items.length}</TableCell>
                    <TableCell><Badge variant="outline" className="capitalize">{o.order_status}</Badge></TableCell>
                    <TableCell><Badge variant="outline" className="capitalize">{o.payment_status}</Badge></TableCell>
                    <TableCell className="text-right">{formatCurrency(o.total_amount)}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </div>
      </div>
    </AppShell>
  );
}
