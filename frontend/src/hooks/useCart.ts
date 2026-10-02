import { useQuery } from "@tanstack/react-query";
import { cartApi } from "@/lib/api/cart";
import { useAuth } from "@/lib/auth/AuthContext";

export function useCart() {
  const { user } = useAuth();
  return useQuery({
    queryKey: ["cart"],
    queryFn: () => cartApi.get(),
    enabled: !!user,
    staleTime: 30_000,
  });
}
