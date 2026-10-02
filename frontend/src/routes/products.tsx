import { createFileRoute } from "@tanstack/react-router";
import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { AppShell } from "@/components/layout/AppShell";
import { ProductGrid } from "@/components/products/ProductGrid";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { productsApi, categoriesApi } from "@/lib/api/products";

interface Search {
  q?: string;
  category?: string;
  min?: number;
  max?: number;
  sort?: "newest" | "price_asc" | "price_desc" | "rating";
  page?: number;
}

export const Route = createFileRoute("/products")({
  validateSearch: (s: Record<string, unknown>): Search => ({
    q: typeof s.q === "string" ? s.q : undefined,
    category: typeof s.category === "string" ? s.category : undefined,
    min: s.min ? Number(s.min) : undefined,
    max: s.max ? Number(s.max) : undefined,
    sort: (["newest", "price_asc", "price_desc", "rating"] as const).includes(s.sort as never)
      ? (s.sort as Search["sort"])
      : undefined,
    page: s.page ? Number(s.page) : undefined,
  }),
  head: () => ({
    meta: [
      { title: "Shop all products — ShopSphere" },
      { name: "description", content: "Browse the full ShopSphere catalog with filters, search, and sorting." },
    ],
  }),
  component: ProductsPage,
});

function ProductsPage() {
  const search = Route.useSearch();
  const navigate = Route.useNavigate();
  const [minLocal, setMinLocal] = useState(search.min?.toString() ?? "");
  const [maxLocal, setMaxLocal] = useState(search.max?.toString() ?? "");

  const categories = useQuery({ queryKey: ["categories"], queryFn: () => categoriesApi.list() });
  const products = useQuery({
    queryKey: ["products", search],
    queryFn: () => productsApi.list({ ...search, limit: 24 }),
  });

  const update = (patch: Partial<Search>) =>
    navigate({ search: (prev: Search) => ({ ...prev, ...patch, page: undefined }) as never });

  return (
    <AppShell>
      <div className="mx-auto max-w-7xl px-4 py-10 sm:px-6 lg:px-8">
        <header className="mb-8">
          <h1 className="font-display text-3xl font-semibold">All products</h1>
          <p className="mt-1 text-sm text-muted-foreground">
            {products.data ? `${products.data.total} results` : "Loading…"}
          </p>
        </header>

        <div className="grid gap-8 lg:grid-cols-[240px_1fr]">
          {/* Filters */}
          <aside className="space-y-6">
            <div>
              <Label className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                Search
              </Label>
              <Input
                value={search.q ?? ""}
                onChange={(e) => update({ q: e.target.value || undefined })}
                placeholder="Find a product"
                className="mt-2"
              />
            </div>

            <div>
              <Label className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                Category
              </Label>
              <Select
                value={search.category ?? "all"}
                onValueChange={(v) => update({ category: v === "all" ? undefined : v })}
              >
                <SelectTrigger className="mt-2">
                  <SelectValue placeholder="All categories" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All categories</SelectItem>
                  {categories.data?.map((c) => (
                    <SelectItem key={c.id} value={c.id}>{c.name}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div>
              <Label className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                Price range
              </Label>
              <div className="mt-2 flex items-center gap-2">
                <Input
                  type="number"
                  placeholder="Min"
                  value={minLocal}
                  onChange={(e) => setMinLocal(e.target.value)}
                />
                <Input
                  type="number"
                  placeholder="Max"
                  value={maxLocal}
                  onChange={(e) => setMaxLocal(e.target.value)}
                />
              </div>
              <Button
                size="sm"
                variant="outline"
                className="mt-2 w-full"
                onClick={() =>
                  update({
                    min: minLocal ? Number(minLocal) : undefined,
                    max: maxLocal ? Number(maxLocal) : undefined,
                  })
                }
              >
                Apply
              </Button>
            </div>

            <div>
              <Label className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                Sort by
              </Label>
              <Select
                value={search.sort ?? "newest"}
                onValueChange={(v) => update({ sort: v as Search["sort"] })}
              >
                <SelectTrigger className="mt-2">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="newest">Newest</SelectItem>
                  <SelectItem value="price_asc">Price: Low to high</SelectItem>
                  <SelectItem value="price_desc">Price: High to low</SelectItem>
                  <SelectItem value="rating">Top rated</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </aside>

          <div>
            <ProductGrid products={products.data?.items} loading={products.isLoading} />
            {products.data && products.data.total > (products.data.limit || 24) && (
              <div className="mt-8 flex items-center justify-center gap-2">
                <Button
                  variant="outline"
                  disabled={(search.page ?? 1) <= 1}
                  onClick={() => navigate({ search: (p: Search) => ({ ...p, page: (p.page ?? 1) - 1 }) as never })}
                >
                  Previous
                </Button>
                <span className="text-sm text-muted-foreground">Page {search.page ?? 1}</span>
                <Button
                  variant="outline"
                  disabled={(search.page ?? 1) * (products.data.limit || 24) >= products.data.total}
                  onClick={() => navigate({ search: (p: Search) => ({ ...p, page: (p.page ?? 1) + 1 }) as never })}
                >
                  Next
                </Button>
              </div>
            )}
          </div>
        </div>
      </div>
    </AppShell>
  );
}
