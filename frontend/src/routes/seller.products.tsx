import { createFileRoute } from "@tanstack/react-router";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { useState } from "react";
import { Plus, Pencil, Trash2 } from "lucide-react";
import { toast } from "sonner";
import type { z } from "zod";
import { AppShell } from "@/components/layout/AppShell";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { RequireAuth } from "@/lib/auth/RequireAuth";
import { productsApi, categoriesApi } from "@/lib/api/products";
import { productSchema } from "@/lib/schemas";
import { formatCurrency } from "@/lib/format";
import type { Product } from "@/lib/types";

export const Route = createFileRoute("/seller/products")({
  component: () => (
    <RequireAuth roles={["seller", "admin"]}>
      <SellerProducts />
    </RequireAuth>
  ),
});

type FormValues = z.infer<typeof productSchema>;

function SellerProducts() {
  const qc = useQueryClient();
  const [open, setOpen] = useState(false);
  const [editing, setEditing] = useState<Product | null>(null);

  const products = useQuery({
    queryKey: ["seller-products"],
    queryFn: () => productsApi.list({ limit: 100 }),
  });
  const categories = useQuery({ queryKey: ["categories"], queryFn: () => categoriesApi.list() });

  const createOrUpdate = useMutation({
    mutationFn: (v: FormValues) =>
      editing ? productsApi.update(editing.id, v) : productsApi.create(v),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["seller-products"] });
      qc.invalidateQueries({ queryKey: ["products"] });
      toast.success(editing ? "Product updated" : "Product created");
      setOpen(false);
      setEditing(null);
    },
    onError: (e: Error) => toast.error(e.message),
  });

  const remove = useMutation({
    mutationFn: (id: string) => productsApi.remove(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["seller-products"] });
      toast.success("Product deleted");
    },
    onError: (e: Error) => toast.error(e.message),
  });

  return (
    <AppShell>
      <div className="mx-auto max-w-6xl px-4 py-10 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="font-display text-3xl font-semibold">Manage products</h1>
            <p className="mt-1 text-sm text-muted-foreground">Create, edit, and remove your listings.</p>
          </div>
          <Dialog open={open} onOpenChange={(o) => { setOpen(o); if (!o) setEditing(null); }}>
            <DialogTrigger asChild>
              <Button onClick={() => setEditing(null)}><Plus className="mr-1 h-4 w-4" /> New product</Button>
            </DialogTrigger>
            <ProductDialog
              key={editing?.id ?? "new"}
              editing={editing}
              categories={categories.data ?? []}
              onSubmit={(v) => createOrUpdate.mutate(v)}
              loading={createOrUpdate.isPending}
            />
          </Dialog>
        </div>

        <div className="mt-8 overflow-hidden rounded-2xl border border-border/60 bg-card">
          {products.isLoading ? (
            <Skeleton className="h-64 w-full" />
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Product</TableHead>
                  <TableHead>Price</TableHead>
                  <TableHead>Stock</TableHead>
                  <TableHead className="text-right">Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {products.data?.items.map((p) => (
                  <TableRow key={p.id}>
                    <TableCell className="font-medium">{p.name}</TableCell>
                    <TableCell>{formatCurrency(p.discount_price ?? p.price)}</TableCell>
                    <TableCell>{p.stock}</TableCell>
                    <TableCell className="text-right">
                      <Button
                        size="icon"
                        variant="ghost"
                        onClick={() => { setEditing(p); setOpen(true); }}
                      >
                        <Pencil className="h-4 w-4" />
                      </Button>
                      <Button
                        size="icon"
                        variant="ghost"
                        onClick={() => { if (confirm(`Delete ${p.name}?`)) remove.mutate(p.id); }}
                      >
                        <Trash2 className="h-4 w-4" />
                      </Button>
                    </TableCell>
                  </TableRow>
                ))}
                {products.data?.items.length === 0 && (
                  <TableRow>
                    <TableCell colSpan={4} className="py-12 text-center text-sm text-muted-foreground">
                      No products yet. Create your first listing.
                    </TableCell>
                  </TableRow>
                )}
              </TableBody>
            </Table>
          )}
        </div>
      </div>
    </AppShell>
  );
}

function ProductDialog({
  editing,
  categories,
  onSubmit,
  loading,
}: {
  editing: Product | null;
  categories: { id: string; name: string }[];
  onSubmit: (v: FormValues) => void;
  loading: boolean;
}) {
  const {
    register,
    handleSubmit,
    setValue,
    watch,
    formState: { errors },
  } = useForm<FormValues>({
    resolver: zodResolver(productSchema),
    defaultValues: editing
      ? {
          name: editing.name,
          description: editing.description,
          price: editing.price,
          discount_price: editing.discount_price ?? undefined,
          stock: editing.stock,
          image_url: editing.image_url ?? undefined,
          category_id: editing.category_id,
        }
      : { stock: 0, price: 0 },
  });

  return (
    <DialogContent className="max-w-lg">
      <DialogHeader>
        <DialogTitle>{editing ? "Edit product" : "New product"}</DialogTitle>
      </DialogHeader>
      <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
        <div className="space-y-1.5">
          <Label>Name</Label>
          <Input {...register("name")} />
          {errors.name && <p className="text-xs text-destructive">{errors.name.message}</p>}
        </div>
        <div className="space-y-1.5">
          <Label>Description</Label>
          <Textarea rows={4} {...register("description")} />
          {errors.description && <p className="text-xs text-destructive">{errors.description.message}</p>}
        </div>
        <div className="grid gap-4 sm:grid-cols-3">
          <div className="space-y-1.5">
            <Label>Price</Label>
            <Input type="number" step="0.01" {...register("price", { valueAsNumber: true })} />
          </div>
          <div className="space-y-1.5">
            <Label>Discount</Label>
            <Input type="number" step="0.01" {...register("discount_price", { valueAsNumber: true })} />
          </div>
          <div className="space-y-1.5">
            <Label>Stock</Label>
            <Input type="number" {...register("stock", { valueAsNumber: true })} />
          </div>
        </div>
        <div className="space-y-1.5">
          <Label>Image URL</Label>
          <Input {...register("image_url")} placeholder="https://…" />
        </div>
        <div className="space-y-1.5">
          <Label>Category</Label>
          <Select
            value={watch("category_id") ?? ""}
            onValueChange={(v) => setValue("category_id", v)}
          >
            <SelectTrigger><SelectValue placeholder="Select category" /></SelectTrigger>
            <SelectContent>
              {categories.map((c) => (
                <SelectItem key={c.id} value={c.id}>{c.name}</SelectItem>
              ))}
            </SelectContent>
          </Select>
          {errors.category_id && <p className="text-xs text-destructive">{errors.category_id.message}</p>}
        </div>
        <Button type="submit" className="w-full" disabled={loading}>
          {loading ? "Saving…" : editing ? "Save changes" : "Create product"}
        </Button>
      </form>
    </DialogContent>
  );
}
