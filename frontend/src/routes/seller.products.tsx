import { createFileRoute } from "@tanstack/react-router";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { useRef, useState } from "react";
import { Plus, Pencil, Trash2, Upload, ImagePlus, X } from "lucide-react";
import { toast } from "sonner";
import type { z } from "zod";
import { AppShell } from "@/components/layout/AppShell";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Switch } from "@/components/ui/switch";
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
import { productsApi } from "@/lib/api/products";
import { categoriesApi } from "@/lib/api/categories";
import { brandsApi } from "@/lib/api/brands";
import { productSchema, variantSchema } from "@/lib/schemas";
import { formatCurrency } from "@/lib/format";
import type { Brand, Product, ProductVariant } from "@/lib/types";
import { useAuth } from "@/lib/auth/AuthContext";

export const Route = createFileRoute("/seller/products")({
  component: () => (
    <RequireAuth roles={["seller", "admin"]}>
      <SellerProducts />
    </RequireAuth>
  ),
});

type FormValues = z.infer<typeof productSchema>;
type VariantValues = z.infer<typeof variantSchema>;

function SellerProducts() {
  const qc = useQueryClient();
  const { user } = useAuth();
  const [open, setOpen] = useState(false);
  const [editing, setEditing] = useState<Product | null>(null);

  const products = useQuery({
    queryKey: ["seller-products", user?.id],
    // Auth + include_inactive: the server scopes the list to the caller's own
    // catalog and includes soft-deleted (inactive) products so they can be
    // restored. For sellers a client-supplied seller_id is overridden; for
    // admins it keeps the page scoped to their own listings.
    queryFn: () =>
      productsApi.list({ limit: 100, include_inactive: true, seller_id: user?.id }),
    enabled: !!user?.id,
  });
  const categories = useQuery({ queryKey: ["categories"], queryFn: () => categoriesApi.list() });
  const brands = useQuery({ queryKey: ["brands"], queryFn: () => brandsApi.list() });

  const invalidate = () => {
    qc.invalidateQueries({ queryKey: ["seller-products"] });
    qc.invalidateQueries({ queryKey: ["products"] });
  };

  const createOrUpdate = useMutation({
    mutationFn: (v: FormValues) => {
      // Normalize blank optional strings to null so the backend clears them
      // (an empty string would clash with the products.sku unique index).
      const payload = {
        ...v,
        sku: v.sku?.trim() ? v.sku : null,
        specifications: v.specifications?.trim() ? v.specifications : null,
        image_url: v.image_url?.trim() ? v.image_url : null,
        discount_price: v.discount_price ?? null,
        brand_id: v.brand_id || null,
      };
      return editing ? productsApi.update(editing.id, payload) : productsApi.create(payload);
    },
    onSuccess: () => {
      invalidate();
      toast.success(editing ? "Product updated" : "Product created");
      setOpen(false);
      setEditing(null);
    },
    onError: (e: Error) => toast.error(e.message),
  });

  const remove = useMutation({
    mutationFn: (id: string) => productsApi.remove(id),
    onSuccess: () => {
      invalidate();
      toast.success("Product deleted");
    },
    onError: (e: Error) => toast.error(e.message),
  });

  const toggleActive = useMutation({
    mutationFn: (p: Product) => productsApi.update(p.id, { is_active: !p.is_active }),
    onSuccess: () => {
      invalidate();
      toast.success("Product status updated");
    },
    onError: (e: Error) => toast.error(e.message),
  });

  return (
    <AppShell>
      <div className="mx-auto max-w-6xl px-4 py-10 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="font-display text-3xl font-semibold">Manage products</h1>
            <p className="mt-1 text-sm text-muted-foreground">
              Create, edit, and remove your listings.
            </p>
          </div>
          <Dialog
            open={open}
            onOpenChange={(o) => {
              setOpen(o);
              if (!o) setEditing(null);
            }}
          >
            <DialogTrigger asChild>
              <Button onClick={() => setEditing(null)}>
                <Plus className="mr-1 h-4 w-4" /> New product
              </Button>
            </DialogTrigger>
            <ProductDialog
              key={editing?.id ?? "new"}
              editing={editing}
              categories={categories.data ?? []}
              brands={brands.data ?? []}
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
                  <TableHead>SKU</TableHead>
                  <TableHead>Price</TableHead>
                  <TableHead>Stock</TableHead>
                  <TableHead>Active</TableHead>
                  <TableHead className="text-right">Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {products.data?.items.map((p) => (
                  <TableRow key={p.id}>
                    <TableCell className="font-medium">{p.name}</TableCell>
                    <TableCell className="font-mono text-xs text-muted-foreground">
                      {p.sku || "—"}
                    </TableCell>
                    <TableCell>{formatCurrency(p.discount_price ?? p.price)}</TableCell>
                    <TableCell>{p.stock}</TableCell>
                    <TableCell>
                      <Switch
                        checked={p.is_active}
                        onCheckedChange={() => toggleActive.mutate(p)}
                        disabled={toggleActive.isPending}
                        aria-label={`Toggle ${p.name}`}
                      />
                    </TableCell>
                    <TableCell className="text-right">
                      <Button
                        size="icon"
                        variant="ghost"
                        onClick={() => {
                          setEditing(p);
                          setOpen(true);
                        }}
                      >
                        <Pencil className="h-4 w-4" />
                      </Button>
                      <Button
                        size="icon"
                        variant="ghost"
                        onClick={() => {
                          if (confirm(`Delete ${p.name}?`)) remove.mutate(p.id);
                        }}
                      >
                        <Trash2 className="h-4 w-4" />
                      </Button>
                    </TableCell>
                  </TableRow>
                ))}
                {products.data?.items.length === 0 && (
                  <TableRow>
                    <TableCell
                      colSpan={6}
                      className="py-12 text-center text-sm text-muted-foreground"
                    >
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
  brands,
  onSubmit,
  loading,
}: {
  editing: Product | null;
  categories: { id: string; name: string }[];
  brands: Brand[];
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
          sku: editing.sku ?? "",
          price: editing.price,
          discount_price: editing.discount_price ?? undefined,
          stock: editing.stock,
          image_url: editing.image_url ?? undefined,
          specifications: editing.specifications ?? "",
          category_id: editing.category_id,
          brand_id: editing.brand_id ?? undefined,
        }
      : { stock: 0, price: 0, sku: "", specifications: "" },
  });

  return (
    <DialogContent className="max-h-[90vh] max-w-2xl overflow-y-auto">
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
          {errors.description && (
            <p className="text-xs text-destructive">{errors.description.message}</p>
          )}
        </div>
        <div className="grid gap-4 sm:grid-cols-3">
          <div className="space-y-1.5">
            <Label>SKU</Label>
            <Input {...register("sku")} placeholder="Optional" />
          </div>
          <div className="space-y-1.5">
            <Label>Price</Label>
            <Input type="number" step="0.01" {...register("price", { valueAsNumber: true })} />
          </div>
          <div className="space-y-1.5">
            <Label>Discount</Label>
            <Input
              type="number"
              step="0.01"
              {...register("discount_price", { valueAsNumber: true })}
            />
          </div>
        </div>
        <div className="space-y-1.5">
          <Label>Stock (when active variants exist, stock = sum of variant stock)</Label>
          <Input type="number" {...register("stock", { valueAsNumber: true })} />
        </div>
        <div className="space-y-1.5">
          <Label>Image URL</Label>
          <Input {...register("image_url")} placeholder="https://…" />
        </div>
        <div className="space-y-1.5">
          <Label>Specifications</Label>
          <Textarea
            rows={3}
            {...register("specifications")}
            placeholder='{"Color": "Black", "Weight": "1.2 kg"}'
            className="font-mono text-xs"
          />
          {errors.specifications && (
            <p className="text-xs text-destructive">{errors.specifications.message}</p>
          )}
        </div>
        <div className="grid gap-4 sm:grid-cols-2">
          <div className="space-y-1.5">
            <Label>Category</Label>
            <Select
              value={watch("category_id") ?? ""}
              onValueChange={(v) => setValue("category_id", v)}
            >
              <SelectTrigger>
                <SelectValue placeholder="Select category" />
              </SelectTrigger>
              <SelectContent>
                {categories.map((c) => (
                  <SelectItem key={c.id} value={c.id}>
                    {c.name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            {errors.category_id && (
              <p className="text-xs text-destructive">{errors.category_id.message}</p>
            )}
          </div>
          <div className="space-y-1.5">
            <Label>Brand</Label>
            <Select
              value={watch("brand_id") ?? "none"}
              onValueChange={(v) => setValue("brand_id", v === "none" ? undefined : v)}
            >
              <SelectTrigger>
                <SelectValue placeholder="No brand" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="none">No brand</SelectItem>
                {brands
                  .filter((b) => b.is_active)
                  .map((b) => (
                    <SelectItem key={b.id} value={b.id}>
                      {b.name}
                    </SelectItem>
                  ))}
              </SelectContent>
            </Select>
          </div>
        </div>
        <Button type="submit" className="w-full" disabled={loading}>
          {loading ? "Saving…" : editing ? "Save changes" : "Create product"}
        </Button>
      </form>

      {editing && (
        <>
          <ImageManager product={editing} />
          <VariantManager product={editing} />
        </>
      )}
    </DialogContent>
  );
}

function ImageManager({ product }: { product: Product }) {
  const qc = useQueryClient();
  const fileRef = useRef<HTMLInputElement>(null);

  const invalidate = () => {
    qc.invalidateQueries({ queryKey: ["seller-products"] });
    qc.invalidateQueries({ queryKey: ["product", product.id] });
  };

  const upload = useMutation({
    mutationFn: (file: File) => productsApi.uploadImage(product.id, file),
    onSuccess: () => {
      toast.success("Image uploaded");
      invalidate();
    },
    onError: (e: Error) => toast.error(e.message),
  });

  const removeImage = useMutation({
    mutationFn: (imageId: string) => productsApi.deleteImage(product.id, imageId),
    onSuccess: () => {
      toast.success("Image removed");
      invalidate();
    },
    onError: (e: Error) => toast.error(e.message),
  });

  return (
    <div className="border-t border-border/60 pt-4">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-semibold">Images</h3>
        <input
          ref={fileRef}
          type="file"
          accept="image/png,image/jpeg,image/webp,image/gif"
          className="hidden"
          disabled={upload.isPending}
          onChange={(e) => {
            const f = e.target.files?.[0];
            if (f) upload.mutate(f);
            e.target.value = "";
          }}
        />
        <Button
          size="sm"
          variant="outline"
          className="gap-1.5"
          disabled={upload.isPending}
          onClick={() => fileRef.current?.click()}
        >
          <Upload className="h-3.5 w-3.5" /> {upload.isPending ? "Uploading…" : "Upload image"}
        </Button>
      </div>
      <div className="mt-3 grid grid-cols-4 gap-2">
        {product.images.map((img) => (
          <div
            key={img.id}
            className="group relative overflow-hidden rounded-lg border border-border/60"
          >
            <img
              src={img.url}
              alt={img.alt_text ?? ""}
              className="aspect-square w-full object-cover"
            />
            <button
              type="button"
              className="absolute right-1 top-1 rounded-full bg-background/90 p-1 opacity-0 transition-opacity group-hover:opacity-100"
              onClick={() => removeImage.mutate(img.id)}
              disabled={removeImage.isPending}
              aria-label="Delete image"
            >
              <X className="h-3 w-3" />
            </button>
          </div>
        ))}
        {product.images.length === 0 && (
          <div className="col-span-4 flex items-center gap-2 text-xs text-muted-foreground">
            <ImagePlus className="h-4 w-4" /> No images — upload up to a 5 MB PNG/JPEG/WebP/GIF.
          </div>
        )}
      </div>
    </div>
  );
}

function VariantManager({ product }: { product: Product }) {
  const qc = useQueryClient();
  const [open, setOpen] = useState(false);
  const [editingVariant, setEditingVariant] = useState<ProductVariant | null>(null);

  const invalidate = () => {
    qc.invalidateQueries({ queryKey: ["seller-products"] });
    qc.invalidateQueries({ queryKey: ["product", product.id] });
  };

  const {
    register,
    handleSubmit,
    reset,
    formState: { errors },
  } = useForm<VariantValues>({
    resolver: zodResolver(variantSchema),
    defaultValues: { sku: "", name: "", price_override: undefined, stock: 0, attributes: "" },
  });

  const save = useMutation({
    mutationFn: (v: VariantValues) => {
      // Blank optional fields are sent as null so the backend clears them
      // (empty overrides/attributes would otherwise be dropped by exclude_unset).
      const payload = {
        ...v,
        price_override: v.price_override == null ? null : v.price_override,
        attributes: v.attributes?.trim() ? v.attributes : null,
      };
      return editingVariant
        ? productsApi.updateVariant(product.id, editingVariant.id, payload)
        : productsApi.createVariant(product.id, payload);
    },
    onSuccess: () => {
      toast.success(editingVariant ? "Variant updated" : "Variant created");
      invalidate();
      setOpen(false);
      setEditingVariant(null);
      reset();
    },
    onError: (e: Error) => toast.error(e.message),
  });

  const remove = useMutation({
    mutationFn: (variantId: string) => productsApi.deleteVariant(product.id, variantId),
    onSuccess: () => {
      toast.success("Variant deleted");
      invalidate();
    },
    onError: (e: Error) => toast.error(e.message),
  });

  return (
    <div className="border-t border-border/60 pt-4">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-semibold">Variants</h3>
        <Dialog open={open} onOpenChange={setOpen}>
          <DialogTrigger asChild>
            <Button
              size="sm"
              variant="outline"
              className="gap-1.5"
              onClick={() => {
                setEditingVariant(null);
                reset({ sku: "", name: "", price_override: undefined, stock: 0, attributes: "" });
              }}
            >
              <Plus className="h-3.5 w-3.5" /> Add variant
            </Button>
          </DialogTrigger>
          <DialogContent className="max-w-md">
            <DialogHeader>
              <DialogTitle>{editingVariant ? "Edit variant" : "New variant"}</DialogTitle>
            </DialogHeader>
            <form onSubmit={handleSubmit((v) => save.mutate(v))} className="space-y-3">
              <div className="grid grid-cols-2 gap-3">
                <div className="space-y-1.5">
                  <Label>SKU</Label>
                  <Input {...register("sku")} />
                  {errors.sku && <p className="text-xs text-destructive">{errors.sku.message}</p>}
                </div>
                <div className="space-y-1.5">
                  <Label>Name</Label>
                  <Input {...register("name")} placeholder="e.g. Size L" />
                  {errors.name && <p className="text-xs text-destructive">{errors.name.message}</p>}
                </div>
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div className="space-y-1.5">
                  <Label>Price override</Label>
                  <Input
                    type="number"
                    step="0.01"
                    {...register("price_override", { valueAsNumber: true })}
                    placeholder="Uses product price"
                  />
                </div>
                <div className="space-y-1.5">
                  <Label>Stock</Label>
                  <Input type="number" {...register("stock", { valueAsNumber: true })} />
                </div>
              </div>
              <div className="space-y-1.5">
                <Label>Attributes</Label>
                <Input {...register("attributes")} placeholder='{"Size": "L", "Color": "Red"}' />
                {errors.attributes && (
                  <p className="text-xs text-destructive">{errors.attributes.message}</p>
                )}
              </div>
              <Button type="submit" className="w-full" disabled={save.isPending}>
                {save.isPending ? "Saving…" : editingVariant ? "Save changes" : "Create variant"}
              </Button>
            </form>
          </DialogContent>
        </Dialog>
      </div>
      <div className="mt-3 space-y-2">
        {product.variants.length === 0 && (
          <p className="text-xs text-muted-foreground">
            Variants let you track stock per option. Product stock is the sum of active variants.
          </p>
        )}
        {product.variants.map((v) => (
          <div
            key={v.id}
            className={`flex items-center justify-between rounded-lg border border-border/60 px-3 py-2 text-sm ${
              v.is_active ? "" : "opacity-50"
            }`}
          >
            <div>
              <span className="font-medium">{v.name}</span>
              <span className="ml-2 font-mono text-xs text-muted-foreground">{v.sku}</span>
              {!v.is_active && <span className="ml-2 text-xs text-muted-foreground">inactive</span>}
            </div>
            <div className="flex items-center gap-3">
              <span className="text-xs text-muted-foreground">
                {v.stock} in stock
                {v.price_override != null && ` · ${formatCurrency(v.price_override)}`}
              </span>
              <Button
                size="icon"
                variant="ghost"
                className="h-7 w-7"
                onClick={() => {
                  setEditingVariant(v);
                  setOpen(true);
                  reset({
                    sku: v.sku,
                    name: v.name,
                    price_override: v.price_override ?? undefined,
                    stock: v.stock,
                    attributes: v.attributes ?? "",
                  });
                }}
              >
                <Pencil className="h-3.5 w-3.5" />
              </Button>
              <Button
                size="icon"
                variant="ghost"
                className="h-7 w-7"
                onClick={() => {
                  if (confirm(`Delete variant ${v.name}?`)) remove.mutate(v.id);
                }}
              >
                <Trash2 className="h-3.5 w-3.5" />
              </Button>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
