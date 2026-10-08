import { z, type ZodNullable, type ZodNumber, type ZodOptional } from "zod";

export const loginSchema = z.object({
  email: z.string().trim().email("Invalid email"),
  password: z.string().min(6, "Min 6 characters"),
});

export const profileSchema = z.object({
  full_name: z.string().trim().min(2, "Name is required").max(100),
  email: z.string().trim().email("Invalid email").max(255),
});

export const changePasswordSchema = z.object({
  current_password: z.string().min(1, "Current password is required"),
  new_password: z.string().min(8, "New password must be at least 8 characters").max(128),
});

export const registerSchema = z.object({
  full_name: z.string().trim().min(2, "Name is required").max(100),
  email: z.string().trim().email("Invalid email").max(255),
  password: z.string().min(8, "Min 8 characters").max(128),
  role: z.enum(["customer", "seller"]),
});

/** JSON object string for specifications / variant attributes. */
export const jsonStringSchema = z
  .string()
  .trim()
  .refine((s) => {
    if (!s) return true;
    try {
      const v = JSON.parse(s);
      return v !== null && typeof v === "object" && !Array.isArray(v);
    } catch {
      return false;
    }
  }, 'Must be a JSON object, e.g. {"Color": "Red"}');

/** Optional money/number field whose empty ("" or NaN — cleared number input) counts as "unset". */
const optionalNum = (min = 0.01): ZodOptional<ZodNullable<ZodNumber>> =>
  z
    .preprocess(
      (v) => (v === "" || (typeof v === "number" && Number.isNaN(v)) ? null : v),
      z.number({ invalid_type_error: "Must be a number" }).min(min),
    )
    .optional()
    .nullable() as unknown as ZodOptional<ZodNullable<ZodNumber>>;

export const productSchema = z.object({
  name: z.string().trim().min(2).max(200),
  description: z.string().trim().min(10).max(5000),
  sku: z.string().trim().min(1).max(64).optional().or(z.literal("")),
  price: z.number().positive(),
  discount_price: optionalNum(0.01),
  stock: z.number().int().nonnegative(),
  image_url: z.string().url().optional().nullable(),
  specifications: jsonStringSchema.optional().or(z.literal("")),
  category_id: z.string().min(1),
  brand_id: z.string().min(1).optional().nullable(),
});

export const variantSchema = z.object({
  sku: z.string().trim().min(1).max(64),
  name: z.string().trim().min(1).max(100),
  price_override: optionalNum(0.01),
  stock: z.number().int().nonnegative(),
  attributes: jsonStringSchema.optional().or(z.literal("")),
});

export const couponSchema = z.object({
  code: z.string().trim().min(1).max(50).toUpperCase(),
  discount_type: z.enum(["percent", "fixed"]),
  discount_value: z.number().positive(),
  min_order_amount: optionalNum(0),
  max_uses: z
    .preprocess(
      (v) => (v === "" || (typeof v === "number" && Number.isNaN(v)) ? null : v),
      z.number({ invalid_type_error: "Must be a number" }).int().positive(),
    )
    .optional()
    .nullable() as unknown as ZodOptional<ZodNullable<ZodNumber>>,
  is_active: z.boolean(),
});

export const checkoutSchema = z.object({
  full_name: z.string().trim().min(2).max(100),
  address_line: z.string().trim().min(5).max(200),
  city: z.string().trim().min(2).max(100),
  postal_code: z.string().trim().min(2).max(20),
  country: z.string().trim().min(2).max(100),
  payment_method: z.enum(["card", "paypal", "cod"]),
});
