import { Link } from "@tanstack/react-router";
import { Store } from "lucide-react";

export function Footer() {
  return (
    <footer className="mt-24 border-t border-border/60 bg-muted/30">
      <div className="mx-auto grid max-w-7xl gap-10 px-4 py-12 sm:px-6 md:grid-cols-4 lg:px-8">
        <div>
          <div className="flex items-center gap-2">
            <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-foreground text-background">
              <Store className="h-4 w-4" />
            </div>
            <span className="font-display text-lg font-semibold">ShopSphere</span>
          </div>
          <p className="mt-3 text-sm text-muted-foreground">
            Production-grade marketplace for sellers, customers, and admins.
          </p>
        </div>
        <div>
          <h4 className="text-sm font-semibold">Shop</h4>
          <ul className="mt-3 space-y-2 text-sm text-muted-foreground">
            <li><Link to="/products" className="hover:text-foreground">All products</Link></li>
            <li><Link to="/" className="hover:text-foreground">Featured</Link></li>
          </ul>
        </div>
        <div>
          <h4 className="text-sm font-semibold">Account</h4>
          <ul className="mt-3 space-y-2 text-sm text-muted-foreground">
            <li><Link to="/login" className="hover:text-foreground">Sign in</Link></li>
            <li><Link to="/register" className="hover:text-foreground">Create account</Link></li>
            <li><Link to="/orders" className="hover:text-foreground">Track orders</Link></li>
          </ul>
        </div>
        <div>
          <h4 className="text-sm font-semibold">Sell</h4>
          <ul className="mt-3 space-y-2 text-sm text-muted-foreground">
            <li><Link to="/seller/products" className="hover:text-foreground">Seller dashboard</Link></li>
            <li><Link to="/register" className="hover:text-foreground">Become a seller</Link></li>
          </ul>
        </div>
      </div>
      <div className="border-t border-border/60 py-6 text-center text-xs text-muted-foreground">
        © {new Date().getFullYear()} ShopSphere — Built on the ShopSphere FastAPI backend.
      </div>
    </footer>
  );
}
