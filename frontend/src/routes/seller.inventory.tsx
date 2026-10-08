import { createFileRoute, Link } from "@tanstack/react-router";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { AlertTriangle, Package, Plus, Minus } from "lucide-react";
import { toast } from "sonner";
import { AppShell } from "@/components/layout/AppShell";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { RequireAuth } from "@/lib/auth/RequireAuth";
import { inventoryApi } from "@/lib/api/inventory";
import type { LowStockItem } from "@/lib/types";

export const Route = createFileRoute("/seller/inventory")({
  component: () => (
    <RequireAuth roles={["seller", "admin"]}>
      <SellerInventory />
    </RequireAuth>
  ),
});

function InventoryRow({ row }: { row: LowStockItem }) {
  const qc = useQueryClient();
  const inv = row.inventory;
  const [delta, setDelta] = useState(1);
  const [note, setNote] = useState("");

  const invalidate = () => qc.invalidateQueries({ queryKey: ["seller-inventory"] });

  const adjust = useMutation({
    mutationFn: (quantity: number) =>
      inventoryApi.adjust(row.product_id, { quantity, note: note || undefined }),
    onSuccess: () => {
      toast.success("Stock adjusted");
      setDelta(1);
      setNote("");
      invalidate();
    },
    onError: (e: Error) => toast.error(e.message),
  });

  const setPhysical = useMutation({
    mutationFn: (physical_stock: number) =>
      inventoryApi.setStock(row.product_id, {
        physical_stock,
        low_stock_threshold: inv.low_stock_threshold,
      }),
    onSuccess: () => {
      toast.success("Stock level set");
      invalidate();
    },
    onError: (e: Error) => toast.error(e.message),
  });

  return (
    <TableRow>
      <TableCell>
        <Link
          to="/products/$id"
          params={{ id: row.product_id }}
          className="font-medium hover:underline"
        >
          {row.product_name}
        </Link>
      </TableCell>
      <TableCell>
        <div className="flex items-center gap-1.5">
          <span className="font-semibold">{inv.physical_stock}</span>
          <span className="text-xs text-muted-foreground">
            ({inv.available_stock} avail · {inv.reserved_stock} reserved)
          </span>
        </div>
      </TableCell>
      <TableCell>
        <Badge
          variant={inv.is_low_stock ? "destructive" : "secondary"}
          className={inv.is_low_stock ? "" : "bg-accent/15 text-accent-foreground"}
        >
          {inv.is_low_stock ? `Low · threshold ${inv.low_stock_threshold}` : "In stock"}
        </Badge>
      </TableCell>
      <TableCell>
        <div className="flex items-center gap-2">
          <Input
            type="number"
            min={1}
            className="h-8 w-20"
            value={delta}
            onChange={(e) => setDelta(Number(e.target.value) || 1)}
          />
          <Button
            size="sm"
            variant="outline"
            className="gap-1"
            disabled={adjust.isPending}
            onClick={() => adjust.mutate(delta)}
            title="Add stock"
          >
            <Plus className="h-3 w-3" /> Add
          </Button>
          <Button
            size="sm"
            variant="outline"
            className="gap-1"
            disabled={adjust.isPending || delta > inv.available_stock}
            onClick={() => adjust.mutate(-delta)}
            title="Remove stock"
          >
            <Minus className="h-3 w-3" /> Remove
          </Button>
          <Button
            size="sm"
            variant="ghost"
            disabled={setPhysical.isPending}
            onClick={() => {
              const v = Number(
                prompt(
                  `Set physical stock for "${row.product_name}" to:`,
                  String(inv.physical_stock),
                ),
              );
              if (Number.isInteger(v) && v >= 0) setPhysical.mutate(v);
            }}
          >
            Set
          </Button>
        </div>
      </TableCell>
      <TableCell>
        {inv.is_low_stock && (
          <div className="flex items-center gap-1.5 text-xs text-destructive">
            <AlertTriangle className="h-3.5 w-3.5" /> Restock soon
          </div>
        )}
      </TableCell>
      <TableCell className="text-right">
        <div className="flex items-center justify-end gap-1.5 text-xs text-muted-foreground">
          {note ? (
            <Input
              className="h-8 w-32"
              placeholder="Note…"
              value={note}
              onChange={(e) => setNote(e.target.value)}
            />
          ) : (
            <Button
              size="sm"
              variant="ghost"
              className="h-8 text-xs"
              onClick={() => setNote("adjust")}
            >
              + note
            </Button>
          )}
        </div>
      </TableCell>
    </TableRow>
  );
}

function SellerInventory() {
  const inventory = useQuery({
    queryKey: ["seller-inventory"],
    queryFn: () => inventoryApi.mine(),
  });
  const low = inventory.data?.filter((r) => r.inventory.is_low_stock) ?? [];

  return (
    <AppShell>
      <div className="mx-auto max-w-6xl px-4 py-10 sm:px-6 lg:px-8">
        <div className="flex items-end justify-between">
          <div>
            <h1 className="font-display text-3xl font-semibold">Inventory</h1>
            <p className="mt-1 text-sm text-muted-foreground">
              Track stock levels and adjust counts for your products.
            </p>
          </div>
          {low.length > 0 && (
            <Badge variant="destructive" className="gap-1.5">
              <AlertTriangle className="h-3.5 w-3.5" /> {low.length} low-stock{" "}
              {low.length === 1 ? "item" : "items"}
            </Badge>
          )}
        </div>

        <div className="mt-8 overflow-hidden rounded-2xl border border-border/60 bg-card">
          {inventory.isLoading ? (
            <Skeleton className="h-64 w-full" />
          ) : !inventory.data?.length ? (
            <div className="p-12 text-center">
              <Package className="mx-auto h-8 w-8 text-muted-foreground" />
              <p className="mt-3 text-sm text-muted-foreground">
                No inventory yet. Create products to start tracking stock.
              </p>
              <Link to="/seller/products">
                <Button className="mt-5" variant="outline">
                  Go to products
                </Button>
              </Link>
            </div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Product</TableHead>
                  <TableHead>Stock</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead>Adjust</TableHead>
                  <TableHead />
                  <TableHead className="text-right">Note</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {inventory.data?.map((row) => (
                  <InventoryRow key={row.product_id} row={row} />
                ))}
              </TableBody>
            </Table>
          )}
        </div>
      </div>
    </AppShell>
  );
}
