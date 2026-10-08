import { createFileRoute, Link } from "@tanstack/react-router";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Heart, ShoppingCart, Trash2, Package } from "lucide-react";
import { toast } from "sonner";
import { AppShell } from "@/components/layout/AppShell";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { RequireAuth } from "@/lib/auth/RequireAuth";
import { wishlistApi } from "@/lib/api/wishlist";
import { formatCurrency } from "@/lib/format";

export const Route = createFileRoute("/wishlist")({
  component: () => (
    <RequireAuth>
      <WishlistPage />
    </RequireAuth>
  ),
});

function WishlistPage() {
  const qc = useQueryClient();
  const wishlist = useQuery({ queryKey: ["wishlist"], queryFn: () => wishlistApi.get() });

  const invalidate = () => {
    qc.invalidateQueries({ queryKey: ["wishlist"] });
    qc.invalidateQueries({ queryKey: ["cart"] });
  };

  const moveToCart = useMutation({
    mutationFn: ({ id, qty }: { id: string; qty: number }) => wishlistApi.moveToCart(id, qty),
    onSuccess: () => {
      toast.success("Moved to cart");
      invalidate();
    },
    onError: (e: Error) => toast.error(e.message),
  });

  const remove = useMutation({
    mutationFn: (id: string) => wishlistApi.remove(id),
    onSuccess: () => {
      toast.success("Removed from wishlist");
      qc.invalidateQueries({ queryKey: ["wishlist"] });
    },
    onError: (e: Error) => toast.error(e.message),
  });

  return (
    <AppShell>
      <div className="mx-auto max-w-5xl px-4 py-10 sm:px-6 lg:px-8">
        <h1 className="font-display text-3xl font-semibold">Your wishlist</h1>

        {wishlist.isLoading ? (
          <Skeleton className="mt-8 h-40 w-full rounded-2xl" />
        ) : !wishlist.data || wishlist.data.items.length === 0 ? (
          <div className="mt-12 rounded-2xl border border-dashed border-border bg-muted/20 p-12 text-center">
            <Heart className="mx-auto h-10 w-10 text-muted-foreground" />
            <p className="mt-4 text-muted-foreground">Nothing saved yet.</p>
            <Link to="/products">
              <Button className="mt-6">Browse products</Button>
            </Link>
          </div>
        ) : (
          <div className="mt-8 space-y-3">
            {wishlist.data.items.map((item) => {
              const p = item.product;
              const price = p.discount_price ?? p.price;
              return (
                <div
                  key={item.id}
                  className="flex gap-4 rounded-2xl border border-border/60 bg-card p-4"
                >
                  <div className="h-24 w-24 overflow-hidden rounded-xl bg-muted">
                    {(p.image_url || p.images?.[0]?.url) && (
                      <img
                        src={p.image_url || p.images?.[0]?.url}
                        alt={p.name}
                        className="h-full w-full object-cover"
                      />
                    )}
                  </div>
                  <div className="flex flex-1 flex-col">
                    <Link
                      to="/products/$id"
                      params={{ id: p.id }}
                      className="text-sm font-medium hover:underline"
                    >
                      {p.name}
                    </Link>
                    <div className="mt-1 text-xs text-muted-foreground">
                      {formatCurrency(price)}
                      {p.stock === 0 && <span className="ml-2 text-destructive">Out of stock</span>}
                    </div>
                    <div className="mt-auto flex items-center gap-2">
                      <Button
                        size="sm"
                        className="gap-1.5"
                        disabled={p.stock === 0 || moveToCart.isPending}
                        onClick={() => moveToCart.mutate({ id: p.id, qty: 1 })}
                      >
                        <ShoppingCart className="h-3.5 w-3.5" /> Add to cart
                      </Button>
                      <Button
                        size="sm"
                        variant="ghost"
                        onClick={() => remove.mutate(p.id)}
                        disabled={remove.isPending}
                      >
                        <Trash2 className="h-3.5 w-3.5" />
                      </Button>
                    </div>
                  </div>
                </div>
              );
            })}
            <div className="flex items-center gap-2 pt-2 text-xs text-muted-foreground">
              <Package className="h-3.5 w-3.5" />
              Items you move to your cart respect any coupon already applied.
            </div>
          </div>
        )}
      </div>
    </AppShell>
  );
}
