import { createFileRoute } from "@tanstack/react-router";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Star, ShoppingCart, Truck, ShieldCheck, RefreshCw } from "lucide-react";
import { useState } from "react";
import { toast } from "sonner";
import { AppShell } from "@/components/layout/AppShell";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { Badge } from "@/components/ui/badge";
import { productsApi } from "@/lib/api/products";
import { cartApi } from "@/lib/api/cart";
import { formatCurrency, formatDate } from "@/lib/format";
import { useAuth } from "@/lib/auth/AuthContext";

export const Route = createFileRoute("/products/$id")({
  component: ProductDetail,
});

function ProductDetail() {
  const { id } = Route.useParams();
  const { user } = useAuth();
  const navigate = Route.useNavigate();
  const qc = useQueryClient();
  const [qty, setQty] = useState(1);

  const product = useQuery({ queryKey: ["product", id], queryFn: () => productsApi.get(id) });
  const reviews = useQuery({ queryKey: ["reviews", id], queryFn: () => productsApi.reviews(id) });

  const addToCart = useMutation({
    mutationFn: () => cartApi.add(id, qty),
    onSuccess: () => {
      toast.success("Added to cart");
      qc.invalidateQueries({ queryKey: ["cart"] });
    },
    onError: (e: Error) => toast.error(e.message || "Could not add to cart"),
  });

  if (product.isLoading) {
    return (
      <AppShell>
        <div className="mx-auto grid max-w-7xl gap-10 px-4 py-10 sm:px-6 md:grid-cols-2 lg:px-8">
          <Skeleton className="aspect-square rounded-2xl" />
          <div className="space-y-4">
            <Skeleton className="h-8 w-3/4" />
            <Skeleton className="h-5 w-1/3" />
            <Skeleton className="h-20 w-full" />
          </div>
        </div>
      </AppShell>
    );
  }

  if (!product.data) {
    return (
      <AppShell>
        <div className="mx-auto max-w-2xl px-4 py-20 text-center">
          <h1 className="text-2xl font-semibold">Product not found</h1>
        </div>
      </AppShell>
    );
  }

  const p = product.data;
  const hasDiscount = p.discount_price != null && p.discount_price < p.price;
  const price = hasDiscount ? p.discount_price! : p.price;

  const handleAdd = () => {
    if (!user) {
      navigate({ to: "/login", search: { redirect: `/products/${id}` } as never });
      return;
    }
    addToCart.mutate();
  };

  return (
    <AppShell>
      <div className="mx-auto max-w-7xl px-4 py-10 sm:px-6 lg:px-8">
        <div className="grid gap-10 md:grid-cols-2">
          <div className="overflow-hidden rounded-2xl border border-border/60 bg-muted">
            {p.image_url ? (
              <img src={p.image_url} alt={p.name} className="aspect-square w-full object-cover" />
            ) : (
              <div className="flex aspect-square items-center justify-center text-sm text-muted-foreground">
                No image
              </div>
            )}
          </div>

          <div className="flex flex-col">
            {p.category?.name && (
              <span className="text-xs font-medium uppercase tracking-wider text-muted-foreground">
                {p.category.name}
              </span>
            )}
            <h1 className="mt-2 font-display text-3xl font-semibold">{p.name}</h1>
            {p.rating != null && (
              <div className="mt-2 flex items-center gap-1.5 text-sm text-muted-foreground">
                <Star className="h-4 w-4 fill-accent text-accent" />
                {p.rating.toFixed(1)} · {p.review_count ?? 0} reviews
              </div>
            )}

            <div className="mt-6 flex items-baseline gap-3">
              <span className="text-3xl font-semibold">{formatCurrency(price)}</span>
              {hasDiscount && (
                <span className="text-lg text-muted-foreground line-through">
                  {formatCurrency(p.price)}
                </span>
              )}
            </div>
            <div className="mt-2">
              {p.stock > 0 ? (
                <Badge variant="secondary" className="bg-accent/15 text-accent-foreground">
                  In stock · {p.stock} available
                </Badge>
              ) : (
                <Badge variant="destructive">Out of stock</Badge>
              )}
            </div>

            <p className="mt-6 whitespace-pre-line text-sm leading-relaxed text-muted-foreground">
              {p.description}
            </p>

            <div className="mt-8 flex items-center gap-3">
              <div className="flex items-center rounded-md border border-input">
                <button
                  type="button"
                  onClick={() => setQty((q) => Math.max(1, q - 1))}
                  className="px-3 py-2 text-sm hover:bg-muted"
                >−</button>
                <span className="w-10 text-center text-sm font-medium">{qty}</span>
                <button
                  type="button"
                  onClick={() => setQty((q) => Math.min(p.stock, q + 1))}
                  className="px-3 py-2 text-sm hover:bg-muted"
                >+</button>
              </div>
              <Button
                size="lg"
                className="flex-1 gap-2"
                onClick={handleAdd}
                disabled={p.stock === 0 || addToCart.isPending}
              >
                <ShoppingCart className="h-4 w-4" />
                {addToCart.isPending ? "Adding…" : "Add to cart"}
              </Button>
            </div>

            <div className="mt-8 grid grid-cols-3 gap-3 border-t border-border/60 pt-6 text-xs text-muted-foreground">
              <div className="flex flex-col items-center gap-1 text-center">
                <Truck className="h-4 w-4 text-accent" /> Fast shipping
              </div>
              <div className="flex flex-col items-center gap-1 text-center">
                <ShieldCheck className="h-4 w-4 text-accent" /> Buyer protection
              </div>
              <div className="flex flex-col items-center gap-1 text-center">
                <RefreshCw className="h-4 w-4 text-accent" /> 30-day returns
              </div>
            </div>
          </div>
        </div>

        {/* Reviews */}
        <section className="mt-16">
          <h2 className="font-display text-2xl font-semibold">Customer reviews</h2>
          <div className="mt-6 space-y-4">
            {reviews.isLoading && <Skeleton className="h-24 w-full rounded-xl" />}
            {reviews.data?.length === 0 && (
              <p className="text-sm text-muted-foreground">No reviews yet.</p>
            )}
            {reviews.data?.map((r) => (
              <div key={r.id} className="rounded-xl border border-border/60 bg-card p-5">
                <div className="flex items-center justify-between">
                  <div className="font-medium">{r.user_name}</div>
                  <div className="flex items-center gap-0.5">
                    {Array.from({ length: 5 }).map((_, i) => (
                      <Star
                        key={i}
                        className={`h-3.5 w-3.5 ${
                          i < r.rating ? "fill-accent text-accent" : "text-muted-foreground/30"
                        }`}
                      />
                    ))}
                  </div>
                </div>
                <p className="mt-2 text-sm text-muted-foreground">{r.comment}</p>
                <div className="mt-2 text-xs text-muted-foreground">{formatDate(r.created_at)}</div>
              </div>
            ))}
          </div>
        </section>
      </div>
    </AppShell>
  );
}
