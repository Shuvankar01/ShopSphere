export const formatCurrency = (n: number | string, currency = "USD") =>
  // Money fields are Decimal on the backend, which pydantic serializes as
  // JSON strings — normalize before formatting.
  new Intl.NumberFormat("en-US", { style: "currency", currency }).format(Number(n));

export const formatDate = (s: string) =>
  new Date(s).toLocaleDateString("en-US", { year: "numeric", month: "short", day: "numeric" });

export const formatDateTime = (s: string) =>
  new Date(s).toLocaleString("en-US", {
    year: "numeric",
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
