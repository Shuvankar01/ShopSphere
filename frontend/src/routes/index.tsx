import { createFileRoute, Link } from "@tanstack/react-router";
import { useQuery } from "@tanstack/react-query";
import { ArrowRight, ShieldCheck, Truck, Sparkles } from "lucide-react";
import { AppShell } from "@/components/layout/AppShell";
import { ProductGrid } from "@/components/products/ProductGrid";
import { Button } from "@/components/ui/button";
import { productsApi, categoriesApi } from "@/lib/api/products";

export const Route = createFileRoute("/")({
  head: () => ({
    meta: [
      { title: "ShopSphere — Modern marketplace" },
      { name: "description", content: "Discover curated products from verified sellers. Fast shipping, secure checkout." },
      { property: "og:title", content: "ShopSphere — Modern marketplace" },
      { property: "og:description", content: "Discover curated products from verified sellers." },
    ],
  }),
  component: Home,
});

function Home() {
  const featured = useQuery({
    queryKey: ["products", "featured"],
    queryFn: () => productsApi.list({ sort: "rating", limit: 8 }),
  });
  const categories = useQuery({
    queryKey: ["categories"],
    queryFn: () => categoriesApi.list(),
  });

  return (
    <AppShell>
      {/* Hero */}
      <section className="relative overflow-hidden border-b border-border/60">
        <div className="absolute inset-0 -z-10 bg-gradient-to-br from-background via-background to-accent/10" />
        <div className="mx-auto grid max-w-7xl gap-10 px-4 py-20 sm:px-6 md:grid-cols-2 md:py-28 lg:px-8">
          <div className="flex flex-col justify-center">
            <span className="mb-4 inline-flex w-fit items-center gap-1.5 rounded-full border border-accent/30 bg-accent/10 px-3 py-1 text-xs font-medium text-accent-foreground">
              <Sparkles className="h-3 w-3" /> New season drops
            </span>
            <h1 className="font-display text-5xl font-semibold leading-tight tracking-tight md:text-6xl">
              Commerce that <span className="text-accent">just works.</span>
            </h1>
            <p className="mt-5 max-w-lg text-lg text-muted-foreground">
              ShopSphere connects customers with independent sellers — from discovery to delivery,
              every step is fast, secure, and built for scale.
            </p>
            <div className="mt-8 flex flex-wrap gap-3">
              <Link to="/products">
                <Button size="lg" className="gap-2">
                  Shop the catalog <ArrowRight className="h-4 w-4" />
                </Button>
              </Link>
              <Link to="/register">
                <Button size="lg" variant="outline">Become a seller</Button>
              </Link>
            </div>
            <div className="mt-10 flex flex-wrap gap-6 text-sm text-muted-foreground">
              <div className="flex items-center gap-2"><Truck className="h-4 w-4 text-accent" /> Free shipping over $50</div>
              <div className="flex items-center gap-2"><ShieldCheck className="h-4 w-4 text-accent" /> Buyer protection</div>
            </div>
          </div>
          <div className="relative hidden md:block">
            <div className="relative aspect-square overflow-hidden rounded-3xl border border-border/60 bg-gradient-to-br from-muted via-background to-accent/20 shadow-xl">
              <div className="absolute inset-0 grid grid-cols-2 grid-rows-2 gap-3 p-6">
                {[1, 2, 3, 4].map((i) => (
                  <div key={i} className="rounded-2xl bg-card shadow-sm" />
                ))}
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Categories */}
      <section className="mx-auto max-w-7xl px-4 py-16 sm:px-6 lg:px-8">
        <div className="mb-8 flex items-end justify-between">
          <div>
            <h2 className="font-display text-3xl font-semibold">Shop by category</h2>
            <p className="mt-1 text-sm text-muted-foreground">Find what you love, faster.</p>
          </div>
        </div>
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-6">
          {categories.isLoading
            ? Array.from({ length: 6 }).map((_, i) => (
                <div key={i} className="aspect-square animate-pulse rounded-2xl bg-muted" />
              ))
            : categories.data?.slice(0, 6).map((c) => (
                <Link
                  key={c.id}
                  to="/products"
                  search={{ category: c.id } as never}
                  className="group flex aspect-square flex-col items-center justify-center rounded-2xl border border-border/60 bg-card p-4 text-center transition-all hover:-translate-y-0.5 hover:border-accent/60 hover:shadow-md"
                >
                  <span className="text-sm font-medium group-hover:text-accent">{c.name}</span>
                </Link>
              ))}
        </div>
      </section>

      {/* Featured */}
      <section className="mx-auto max-w-7xl px-4 pb-20 sm:px-6 lg:px-8">
        <div className="mb-8 flex items-end justify-between">
          <div>
            <h2 className="font-display text-3xl font-semibold">Top rated</h2>
            <p className="mt-1 text-sm text-muted-foreground">Hand-picked by the community.</p>
          </div>
          <Link to="/products" className="text-sm font-medium text-accent hover:underline">
            View all →
          </Link>
        </div>
        <ProductGrid
          products={featured.data?.items}
          loading={featured.isLoading}
          empty="No products yet — start the FastAPI backend and seed some products."
        />
      </section>
    </AppShell>
  );
}
