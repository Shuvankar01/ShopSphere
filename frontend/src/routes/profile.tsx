import { createFileRoute } from "@tanstack/react-router";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation } from "@tanstack/react-query";
import { toast } from "sonner";
import type { z } from "zod";
import { AppShell } from "@/components/layout/AppShell";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { RequireAuth } from "@/lib/auth/RequireAuth";
import { useAuth } from "@/lib/auth/AuthContext";
import { usersApi } from "@/lib/api/users";
import { authApi } from "@/lib/api/auth";
import { profileSchema, changePasswordSchema } from "@/lib/schemas";

export const Route = createFileRoute("/profile")({
  component: () => (
    <RequireAuth>
      <ProfilePage />
    </RequireAuth>
  ),
});

type FormValues = z.infer<typeof profileSchema>;

function ProfilePage() {
  const { user, refresh } = useAuth();
  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<FormValues>({
    resolver: zodResolver(profileSchema),
    defaultValues: { full_name: user?.full_name ?? "", email: user?.email ?? "" },
  });

  const save = useMutation({
    mutationFn: (v: FormValues) => usersApi.updateProfile(v),
    onSuccess: async () => {
      toast.success("Profile updated");
      await refresh();
    },
    onError: (e: Error) => toast.error(e.message),
  });

  return (
    <AppShell>
      <div className="mx-auto max-w-xl px-4 py-10 sm:px-6 lg:px-8">
        <h1 className="font-display text-3xl font-semibold">Profile</h1>
        <p className="mt-1 text-sm text-muted-foreground capitalize">Role: {user?.role}</p>

        <form
          onSubmit={handleSubmit((v) => save.mutate(v))}
          className="mt-8 space-y-4 rounded-2xl border border-border/60 bg-card p-6"
        >
          <div className="space-y-1.5">
            <Label>Full name</Label>
            <Input {...register("full_name")} />
            {errors.full_name && (
              <p className="text-xs text-destructive">{errors.full_name.message}</p>
            )}
          </div>
          <div className="space-y-1.5">
            <Label>Email</Label>
            <Input type="email" {...register("email")} />
            {errors.email && <p className="text-xs text-destructive">{errors.email.message}</p>}
          </div>
          <Button type="submit" disabled={save.isPending}>
            {save.isPending ? "Saving…" : "Save changes"}
          </Button>
        </form>

        <ChangePasswordCard />
      </div>
    </AppShell>
  );
}

type ChangePasswordValues = z.infer<typeof changePasswordSchema>;

function ChangePasswordCard() {
  const {
    register,
    handleSubmit,
    reset,
    formState: { errors },
  } = useForm<ChangePasswordValues>({
    resolver: zodResolver(changePasswordSchema),
  });

  const change = useMutation({
    mutationFn: (v: ChangePasswordValues) => authApi.changePassword(v),
    onSuccess: () => {
      toast.success("Password updated");
      reset();
    },
    onError: (e: Error) => toast.error(e.message),
  });

  return (
    <form
      onSubmit={handleSubmit((v) => change.mutate(v))}
      className="mt-6 space-y-4 rounded-2xl border border-border/60 bg-card p-6"
    >
      <div>
        <h2 className="font-display text-xl font-semibold">Change password</h2>
        <p className="text-sm text-muted-foreground">
          Confirm your current password, then choose a new one.
        </p>
      </div>
      <div className="space-y-1.5">
        <Label>Current password</Label>
        <Input type="password" autoComplete="current-password" {...register("current_password")} />
        {errors.current_password && (
          <p className="text-xs text-destructive">{errors.current_password.message}</p>
        )}
      </div>
      <div className="space-y-1.5">
        <Label>New password</Label>
        <Input type="password" autoComplete="new-password" {...register("new_password")} />
        {errors.new_password && (
          <p className="text-xs text-destructive">{errors.new_password.message}</p>
        )}
      </div>
      <Button type="submit" disabled={change.isPending}>
        {change.isPending ? "Updating…" : "Update password"}
      </Button>
    </form>
  );
}
