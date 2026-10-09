import { createFileRoute } from "@tanstack/react-router";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  Star,
  ShoppingCart,
  Truck,
  ShieldCheck,
  RefreshCw,
  Heart,
  BadgePercent,
} from "lucide-react";
import { useMemo, useState } from "react";
import { toast } from "sonner";
import { AppShell } from "@/components/layout/AppShell";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { Badge } from "@/components/ui/badge";
import { Textarea } from "@/components/ui/textarea";
import { productsApi } from "@/lib/api/products";
import { cartApi } from "@/lib/api/cart";
import { wishlistApi } from "@/lib/api/wishlist";
import { formatCurrency, formatDate } from "@/lib/format";
import { useAuth } from "@/lib/auth/AuthContext";
import { ProductGrid } from "@/components/products/ProductGrid";

export const Route = createFileRoute("/products/$id")({
  component: ProductDetail,
});

interface Specs {
  entries: [string, string][];
}

function parseSpecs(specs: string | null | undefined): Specs {
  if (!specs) return { entries: [] };
  try {
    const parsed = JSON.parse(specs);
    if (parsed && typeof parsed === "object" && !Array.isArray(parsed)) {
      const entries = Object.entries(parsed).filter(([, v]) => typeof v === "string") as [
        string,
        string,
      ][];
      return { entries };
    }
  } catch {
    /* ignore malformed spec JSON */
  }
  return { entries: [] };
}

function ProductDetail() {
  const { id } = Route.useParams();
  const { user } = useAuth();
  const navigate = Route.useNavigate();
  const qc = useQueryClient();
  const [qty, setQty] = useState(1);
  const [variantId, setVariantId] = useState<string | null>(null);
  const [activeImage, setActiveImage] = useState(0);
  const [reviewRating, setReviewRating] = useState(5);
  const [reviewComment, setReviewComment] = useState("");

  const product = useQuery({ queryKey: ["product", id], queryFn: () => productsApi.get(id) });
  const reviews = useQuery({ queryKey: ["reviews", id], queryFn: () => productsApi.reviews(id) });
  const related = useQuery({ queryKey: ["related", id], queryFn: () => productsApi.related(id) });
  const wishlist = useQuery({
    queryKey: ["wishlist"],
    queryFn: () => wishlistApi.get(),
    enabled: !!user,
  });
  const specs = useMemo(
    () => parseSpecs(product.data?.specifications),
    [product.data?.specifications],
  );

  const addToCart = useMutation({
    mutationFn: () => cartApi.add(id, qty),
    onSuccess: () => {
      toast.success("Added to cart");
      qc.invalidateQueries({ queryKey: ["cart"] });
    },
    onError: (e: Error) => toast.error(e.message || "Could not add to cart"),
  });

  const toggleWishlist = useMutation({
    mutationFn: () => {
      const inWishlist = wishlist.data?.items.some((i) => i.product_id === id) ?? false;
      return inWishlist ? wishlistApi.remove(id) : wishlistApi.add(id);
    },
    onSuccess: () => {
      const inWishlist = wishlist.data?.items.some((i) => i.product_id === id) ?? false;
      toast.success(inWishlist ? "Removed from wishlist" : "Saved to wishlist");
      qc.invalidateQueries({ queryKey: ["wishlist"] });
    },
    onError: (e: Error) => toast.error(e.message),
  });

  const submitReview = useMutation({
    mutationFn: () => productsApi.addReview(id, { rating: reviewRating, comment: reviewComment }),
    onSuccess: () => {
      toast.success("Review submitted");
      setReviewComment("");
      setReviewRating(5);
      qc.invalidateQueries({ queryKey: ["reviews", id] });
      qc.invalidateQueries({ queryKey: ["product", id] });
      qc.invalidateQueries({ queryKey: ["products"] });
    },
    onError: (e: Error) => toast.error(e.message),
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
  const activeVariants = p.variants.filter((v) => v.is_active && v.stock > 0);
  const selectedVariant = activeVariants.find((v) => v.id === variantId) ?? null;

  const basePrice = hasDiscount ? p.discount_price! : p.price;
  const displayPrice = selectedVariant?.price_override ?? basePrice;
  const stock = selectedVariant ? selectedVariant.stock : p.stock;
  const displaySku = selectedVariant?.sku ?? p.sku;

  const gallery = p.images.length > 0 ? p.images : p.image_url ? [{ url: p.image_url }] : [];
  const safeImageIndex = Math.min(activeImage, Math.max(0, gallery.length - 1));
  const currentImage = gallery[safeImageIndex];

  const inWishlist = wishlist.data?.items.some((i) => i.product_id === id) ?? false;
  const alreadyReviewed =
    !!user && (reviews.data?.some((r) => r.user_id === user.id && r.product_id === id) ?? false);

  const handleAdd = () => {
    if (!user) {
      navigate({ to: "/login", search: { redirect: `/products/${id}` } as never });
      return;
    }
    addToCart.mutate();
  };

  const handleWishlist = () => {
    if (!user) {
      navigate({ to: "/login", search: { redirect: `/products/${id}` } as never });
      return;
    }
    toggleWishlist.mutate();
  };

  return (
    <AppShell>
      <div className="mx-auto max-w-7xl px-4 py-10 sm:px-6 lg:px-8">
        <div className="grid gap-10 md:grid-cols-2">
          <div>
            <div className="overflow-hidden rounded-2xl border border-border/60 bg-muted">
              {currentImage ? (
                <img
                  src={currentImage.url}
                  alt={p.name}
                  className="aspect-square w-full object-cover"
                />
              ) : (
                <div className="flex aspect-square items-center justify-center text-sm text-muted-foreground">
                  No image
                </div>
              )}
            </div>
            {gallery.length > 1 && (
              <div className="mt-3 flex gap-2">
                {gallery.map((img, i) => (
                  <button
                    key={img.url + i}
                    type="button"
                    onClick={() => setActiveImage(i)}
                    className={`h-16 w-16 overflow-hidden rounded-lg border ${
                      i === safeImageIndex ? "border-accent" : "border-border/60"
                    }`}
                  >
                    <img src={img.url} alt="" className="h-full w-full object-cover" />
                  </button>
                ))}
              </div>
            )}
          </div>

          <div className="flex flex-col">
            <div className="flex items-center justify-between gap-2">
              <span className="text-xs font-medium uppercase tracking-wider text-muted-foreground">
                {p.category?.name}
              </span>
              <Button
                variant="ghost"
                size="sm"
                className={inWishlist ? "text-accent" : "text-muted-foreground"}
                onClick={handleWishlist}
                disabled={toggleWishlist.isPending}
              >
                <Heart className={`mr-1.5 h-4 w-4 ${inWishlist ? "fill-accent" : ""}`} />
                {inWishlist ? "Saved" : "Save to wishlist"}
              </Button>
            </div>
            <h1 className="mt-2 font-display text-3xl font-semibold">{p.name}</h1>
            {p.brand?.name && (
              <div className="mt-1 text-sm text-muted-foreground">Brand · {p.brand.name}</div>
            )}
            {p.rating != null && (
              <div className="mt-2 flex items-center gap-1.5 text-sm text-muted-foreground">
                <Star className="h-4 w-4 fill-accent text-accent" />
                {p.rating.toFixed(1)} · {p.review_count ?? 0} reviews
              </div>
            )}

            <div className="mt-6 flex items-baseline gap-3">
              <span className="text-3xl font-semibold">{formatCurrency(displayPrice)}</span>
              {hasDiscount && !selectedVariant && (
                <span className="text-lg text-muted-foreground line-through">
                  {formatCurrency(p.price)}
                </span>
              )}
            </div>
            <div className="mt-2 flex items-center gap-2">
              {stock > 0 ? (
                <Badge variant="secondary" className="bg-accent/15 text-accent-foreground">
                  In stock · {stock} available
                </Badge>
              ) : (
                <Badge variant="destructive">Out of stock</Badge>
              )}
              {displaySku && (
                <span className="text-xs text-muted-foreground">SKU: {displaySku}</span>
              )}
            </div>

            {/* Variant selector */}
            {p.variants.length > 0 && (
              <div className="mt-6">
                <div className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                  Options
                </div>
                <div className="mt-2 flex flex-wrap gap-2">
                  {p.variants
                    .filter((v) => v.is_active)
                    .map((v) => (
                      <button
                        key={v.id}
                        type="button"
                        onClick={() => setVariantId(v.id)}
                        disabled={v.stock === 0}
                        className={`rounded-lg border px-3 py-1.5 text-sm transition-colors ${
                          v.id === variantId
                            ? "border-accent bg-accent/10 font-medium text-accent"
                            : v.stock === 0
                              ? "cursor-not-allowed border-border/40 opacity-50"
                              : "border-border/60 hover:border-accent/50"
                        }`}
                      >
                        {v.name}
                        {v.stock === 0 && " · sold out"}
                      </button>
                    ))}
                </div>
              </div>
            )}

            <p className="mt-6 whitespace-pre-line text-sm leading-relaxed text-muted-foreground">
              {p.description}
            </p>

            <div className="mt-8 flex items-center gap-3">
              <div className="flex items-center rounded-md border border-input">
                <button
                  type="button"
                  onClick={() => setQty((q) => Math.max(1, q - 1))}
                  className="px-3 py-2 text-sm hover:bg-muted"
                >
                  −
                </button>
                <span className="w-10 text-center text-sm font-medium">{qty}</span>
                <button
                  type="button"
                  onClick={() => setQty((q) => Math.min(Math.max(1, stock), q + 1))}
                  className="px-3 py-2 text-sm hover:bg-muted"
                >
                  +
                </button>
              </div>
              <Button
                size="lg"
                className="flex-1 gap-2"
                onClick={handleAdd}
                disabled={stock === 0 || addToCart.isPending}
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

        {/* Specifications */}
        {specs.entries.length > 0 && (
          <section className="mt-16">
            <h2 className="font-display text-2xl font-semibold">Specifications</h2>
            <div className="mt-6 overflow-hidden rounded-2xl border border-border/60 bg-card">
              <table className="w-full divide-y divide-border/60 text-sm">
                <tbody>
                  {specs.entries.map(([k, v]) => (
                    <tr key={k} className="divide-x divide-border/60">
                      <th className="w-1/3 bg-muted/40 px-4 py-3 text-left font-medium">
                        <span className="inline-flex items-center gap-1.5">
                          <BadgePercent className="h-3.5 w-3.5 text-accent" /> {k}
                        </span>
                      </th>
                      <td className="px-4 py-3 text-muted-foreground">{v}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>
        )}

        {/* Reviews */}
        <section className="mt-16">
          <h2 className="font-display text-2xl font-semibold">Customer reviews</h2>
          {user && !alreadyReviewed && (
            <div className="mt-6 rounded-2xl border border-border/60 bg-card p-5">
              <div className="flex items-center gap-1">
                {Array.from({ length: 5 }).map((_, i) => (
                  <button
                    key={i}
                    type="button"
                    onClick={() => setReviewRating(i + 1)}
                    aria-label={`${i + 1} stars`}
                  >
                    <Star
                      className={`h-5 w-5 ${
                        i < reviewRating ? "fill-accent text-accent" : "text-muted-foreground/40"
                      }`}
                    />
                  </button>
                ))}
                <span className="ml-2 text-sm text-muted-foreground">{reviewRating} / 5</span>
              </div>
              <Textarea
                rows={3}
                className="mt-3"
                placeholder="Share your experience with this product…"
                value={reviewComment}
                onChange={(e) => setReviewComment(e.target.value)}
              />
              <Button
                size="sm"
                className="mt-3"
                disabled={reviewComment.trim().length < 3 || submitReview.isPending}
                onClick={() => submitReview.mutate()}
              >
                {submitReview.isPending ? "Submitting…" : "Submit review"}
              </Button>
            </div>
          )}
          {user && alreadyReviewed && (
            <p className="mt-4 text-sm text-muted-foreground">
              You've already reviewed this product.
            </p>
          )}

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

        {/* Related products */}
        {related.data && related.data.items.length > 0 && (
          <section className="mt-16">
            <h2 className="font-display text-2xl font-semibold">Related products</h2>
            <div className="mt-6">
              <ProductGrid products={related.data.items.slice(0, 4)} loading={related.isLoading} />
            </div>
          </section>
        )}
      </div>
    </AppShell>
  );
}
