/**
 * Decimal normalization helpers.
 *
 * The backend serializes every Decimal (money, ratings, discounts) as a JSON
 * string (e.g. "49.99"). These helpers convert them to numbers on the client
 * so the rest of the app can do arithmetic and comparisons safely.
 */
export const num = (v: unknown): number | undefined =>
  v === null || v === undefined || v === "" ? undefined : Number(v);

export const numOrNull = (v: unknown): number | null =>
  v === null || v === undefined || v === "" ? null : Number(v);
