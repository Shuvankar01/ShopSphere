import { createFileRoute } from "@tanstack/react-router";
import { useQuery } from "@tanstack/react-query";
import { AppShell } from "@/components/layout/AppShell";
import { Skeleton } from "@/components/ui/skeleton";
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
import { formatCurrency } from "@/lib/format";

export const Route = createFileRoute("/admin/products")({
  component: () => (
    <RequireAuth roles={["admin"]}>
      <AdminProducts />
    </RequireAuth>
  ),
});

function AdminProducts() {
  const products = useQuery({ queryKey: ["admin-products"], queryFn: () => adminApi.products() });
  return (
    <AppShell>
      <div className="mx-auto max-w-6xl px-4 py-10 sm:px-6 lg:px-8">
        <h1 className="font-display text-3xl font-semibold">All products</h1>
        <div className="mt-8 overflow-hidden rounded-2xl border border-border/60 bg-card">
          {products.isLoading ? (
            <Skeleton className="h-64 w-full" />
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Name</TableHead>
                  <TableHead>Price</TableHead>
                  <TableHead>Stock</TableHead>
                  <TableHead>Seller</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {products.data?.map((p) => (
                  <TableRow key={p.id}>
                    <TableCell className="font-medium">{p.name}</TableCell>
                    <TableCell>{formatCurrency(p.discount_price ?? p.price)}</TableCell>
                    <TableCell>{p.stock}</TableCell>
                    <TableCell className="font-mono text-xs">{p.seller_id.slice(0, 8)}</TableCell>
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
