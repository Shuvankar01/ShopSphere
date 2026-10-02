import { createFileRoute, Link, useNavigate } from "@tanstack/react-router";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { useState } from "react";
import { toast } from "sonner";
import type { z } from "zod";
import { AppShell } from "@/components/layout/AppShell";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group";
import { registerSchema } from "@/lib/schemas";
import { useAuth } from "@/lib/auth/AuthContext";

export const Route = createFileRoute("/register")({
  component: RegisterPage,
});

type FormValues = z.infer<typeof registerSchema>;

function RegisterPage() {
  const { register: registerUser } = useAuth();
  const navigate = useNavigate();
  const [loading, setLoading] = useState(false);
  const {
    register,
    handleSubmit,
    setValue,
    watch,
    formState: { errors },
  } = useForm<FormValues>({
    resolver: zodResolver(registerSchema),
    defaultValues: { role: "customer" },
  });

  const role = watch("role");

  const onSubmit = async (values: FormValues) => {
    setLoading(true);
    try {
      await registerUser(values);
      toast.success("Account created");
      navigate({ to: "/dashboard" });
    } catch (e) {
      toast.error((e as Error).message || "Could not register");
    } finally {
      setLoading(false);
    }
  };

  return (
    <AppShell>
      <div className="mx-auto flex min-h-[70vh] max-w-md flex-col justify-center px-4 py-12">
        <h1 className="font-display text-3xl font-semibold">Create your account</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Start shopping or selling on ShopSphere.
        </p>
        <form onSubmit={handleSubmit(onSubmit)} className="mt-8 space-y-4">
          <div className="space-y-1.5">
            <Label htmlFor="full_name">Full name</Label>
            <Input id="full_name" autoComplete="name" {...register("full_name")} />
            {errors.full_name && <p className="text-xs text-destructive">{errors.full_name.message}</p>}
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="email">Email</Label>
            <Input id="email" type="email" autoComplete="email" {...register("email")} />
            {errors.email && <p className="text-xs text-destructive">{errors.email.message}</p>}
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="password">Password</Label>
            <Input id="password" type="password" autoComplete="new-password" {...register("password")} />
            {errors.password && <p className="text-xs text-destructive">{errors.password.message}</p>}
          </div>
          <div className="space-y-2">
            <Label>I want to</Label>
            <RadioGroup
              value={role}
              onValueChange={(v) => setValue("role", v as "customer" | "seller")}
              className="grid grid-cols-2 gap-2"
            >
              <Label htmlFor="r-customer" className="flex cursor-pointer items-center gap-2 rounded-md border border-input p-3 hover:bg-muted/40 has-[:checked]:border-accent has-[:checked]:bg-accent/10">
                <RadioGroupItem id="r-customer" value="customer" />
                <span className="text-sm">Shop</span>
              </Label>
              <Label htmlFor="r-seller" className="flex cursor-pointer items-center gap-2 rounded-md border border-input p-3 hover:bg-muted/40 has-[:checked]:border-accent has-[:checked]:bg-accent/10">
                <RadioGroupItem id="r-seller" value="seller" />
                <span className="text-sm">Sell</span>
              </Label>
            </RadioGroup>
          </div>
          <Button type="submit" className="w-full" disabled={loading}>
            {loading ? "Creating…" : "Create account"}
          </Button>
        </form>
        <p className="mt-6 text-center text-sm text-muted-foreground">
          Already have an account?{" "}
          <Link to="/login" className="font-medium text-accent hover:underline">
            Sign in
          </Link>
        </p>
      </div>
    </AppShell>
  );
}
