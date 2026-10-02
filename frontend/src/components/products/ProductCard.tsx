import { Link } from "@tanstack/react-router";
import { Star } from "lucide-react";
import { formatCurrency } from "@/lib/format";
import type { Product } from "@/lib/types";

export function ProductCard({ product }: { product: Product }) {
  const hasDiscount = product.discount_price != null && product.discount_price < product.price;
  const price = hasDiscount ? product.discount_price! : product.price;

  return (
    <Link
      to="/products/$id"
      params={{ id: product.id }}
      className="group flex flex-col overflow-hidden rounded-2xl border border-border/60 bg-card transition-all hover:-translate-y-0.5 hover:shadow-lg"
    >
      <div className="relative aspect-square overflow-hidden bg-muted">
        {product.image_url ? (
          // eslint-disable-next-line @next/next/no-img-element
          <img
            src={product.image_url}
            alt={product.name}
            className="h-full w-full object-cover transition-transform duration-500 group-hover:scale-105"
          />
        ) : (
          <div className="flex h-full items-center justify-center text-xs text-muted-foreground">
            No image
          </div>
        )}
        {hasDiscount && (
          <span className="absolute left-3 top-3 rounded-full bg-accent px-2 py-0.5 text-[10px] font-semibold text-accent-foreground">
            SALE
          </span>
        )}
      </div>
      <div className="flex flex-1 flex-col gap-1 p-4">
        {product.category?.name && (
          <span className="text-[11px] font-medium uppercase tracking-wider text-muted-foreground">
            {product.category.name}
          </span>
        )}
        <h3 className="line-clamp-2 text-sm font-medium text-foreground">{product.name}</h3>
        <div className="mt-auto flex items-end justify-between pt-2">
          <div>
            <div className="font-semibold">{formatCurrency(price)}</div>
            {hasDiscount && (
              <div className="text-xs text-muted-foreground line-through">
                {formatCurrency(product.price)}
              </div>
            )}
          </div>
          {product.rating != null && (
            <div className="flex items-center gap-1 text-xs text-muted-foreground">
              <Star className="h-3 w-3 fill-accent text-accent" />
              {product.rating.toFixed(1)}
            </div>
          )}
        </div>
      </div>
    </Link>
  );
}
