import { z } from "zod";

export const loginSchema = z.object({
  email: z.string().trim().email("Invalid email"),
  password: z.string().min(6, "Min 6 characters"),
});

export const registerSchema = z.object({
  full_name: z.string().trim().min(2, "Name is required").max(100),
  email: z.string().trim().email("Invalid email").max(255),
  password: z.string().min(8, "Min 8 characters").max(128),
  role: z.enum(["customer", "seller"]),
});

export const productSchema = z.object({
  name: z.string().trim().min(2).max(200),
  description: z.string().trim().min(10).max(5000),
  price: z.number().positive(),
  discount_price: z.number().positive().optional().nullable(),
  stock: z.number().int().nonnegative(),
  image_url: z.string().url().optional().nullable(),
  category_id: z.string().min(1),
});

export const checkoutSchema = z.object({
  full_name: z.string().trim().min(2).max(100),
  address_line: z.string().trim().min(5).max(200),
  city: z.string().trim().min(2).max(100),
  postal_code: z.string().trim().min(2).max(20),
  country: z.string().trim().min(2).max(100),
  payment_method: z.enum(["card", "paypal", "cod"]),
});

export const profileSchema = z.object({
  full_name: z.string().trim().min(2).max(100),
  email: z.string().trim().email().max(255),
});

export const reviewSchema = z.object({
  rating: z.number().int().min(1).max(5),
  comment: z.string().trim().min(3).max(1000),
});
