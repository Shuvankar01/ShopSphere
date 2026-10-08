import { createFileRoute } from "@tanstack/react-router";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { useState } from "react";
import { Plus, Pencil, Power, Ticket } from "lucide-react";
import { toast } from "sonner";
import type { z } from "zod";
import { AppShell } from "@/components/layout/AppShell";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import { Badge } from "@/components/ui/badge";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Skeleton } from "@/components/ui/skeleton";
import { RequireAuth } from "@/lib/auth/RequireAuth";
import { couponsApi } from "@/lib/api/coupons";
import { couponSchema } from "@/lib/schemas";
import { formatCurrency, formatDate } from "@/lib/format";
import type { Coupon } from "@/lib/types";

export const Route = createFileRoute("/admin/coupons")({
  component: () => (
    <RequireAuth roles={["admin"]}>
      <AdminCoupons />
    </RequireAuth>
  ),
});

type FormValues = z.infer<typeof couponSchema>;

function AdminCoupons() {
  const qc = useQueryClient();
  const [open, setOpen] = useState(false);
  const [editing, setEditing] = useState<Coupon | null>(null);

  const coupons = useQuery({ queryKey: ["admin-coupons"], queryFn: () => couponsApi.list() });

  const invalidate = () => {
    qc.invalidateQueries({ queryKey: ["admin-coupons"] });
    qc.invalidateQueries({ queryKey: ["cart"] });
  };

  const save = useMutation({
    mutationFn: (v: FormValues) => {
      // Blank optional fields are sent as null so the backend clears them.
      const payload = {
        ...v,
        min_order_amount: v.min_order_amount == null ? null : v.min_order_amount,
        max_uses: v.max_uses == null ? null : v.max_uses,
      };
      return editing ? couponsApi.update(editing.id, payload) : couponsApi.create(payload);
    },
    onSuccess: () => {
      invalidate();
      toast.success(editing ? "Coupon updated" : "Coupon created");
      setOpen(false);
      setEditing(null);
    },
    onError: (e: Error) => toast.error(e.message),
  });

  const deactivate = useMutation({
    mutationFn: async (c: Coupon) => {
      if (c.is_active) {
        await couponsApi.deactivate(c.id);
      } else {
        await couponsApi.update(c.id, { is_active: true });
      }
    },
    onSuccess: () => {
      invalidate();
      toast.success("Coupon status updated");
    },
    onError: (e: Error) => toast.error(e.message),
  });

  return (
    <AppShell>
      <div className="mx-auto max-w-5xl px-4 py-10 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="font-display text-3xl font-semibold">Coupons</h1>
            <p className="mt-1 text-sm text-muted-foreground">
              Create discount codes customers can apply at checkout. Usage is recorded once per
              order.
            </p>
          </div>
          <Dialog
            open={open}
            onOpenChange={(o) => {
              setOpen(o);
              if (!o) setEditing(null);
            }}
          >
            <DialogTrigger asChild>
              <Button onClick={() => setEditing(null)}>
                <Plus className="mr-1 h-4 w-4" /> New coupon
              </Button>
            </DialogTrigger>
            <CouponDialog
              key={editing?.id ?? "new"}
              editing={editing}
              onSubmit={(v) => save.mutate(v)}
              loading={save.isPending}
            />
          </Dialog>
        </div>

        <div className="mt-8 overflow-hidden rounded-2xl border border-border/60 bg-card">
          {coupons.isLoading ? (
            <Skeleton className="h-64 w-full" />
          ) : !coupons.data?.length ? (
            <div className="p-12 text-center">
              <Ticket className="mx-auto h-8 w-8 text-muted-foreground" />
              <p className="mt-3 text-sm text-muted-foreground">
                No coupons yet. Create your first code.
              </p>
            </div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Code</TableHead>
                  <TableHead>Discount</TableHead>
                  <TableHead>Usage</TableHead>
                  <TableHead>Min order</TableHead>
                  <TableHead>Created</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead className="text-right">Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {coupons.data.map((c) => (
                  <TableRow key={c.id} className={c.is_active ? "" : "opacity-60"}>
                    <TableCell className="font-mono font-semibold uppercase">{c.code}</TableCell>
                    <TableCell>
                      {c.discount_type === "percent"
                        ? `${c.discount_value}%`
                        : formatCurrency(c.discount_value)}
                    </TableCell>
                    <TableCell>
                      {c.used_count}
                      {c.max_uses != null ? ` / ${c.max_uses}` : ""}
                    </TableCell>
                    <TableCell>
                      {c.min_order_amount != null ? formatCurrency(c.min_order_amount) : "—"}
                    </TableCell>
                    <TableCell className="text-xs text-muted-foreground">
                      {formatDate(c.created_at)}
                    </TableCell>
                    <TableCell>
                      <Badge variant={c.is_active ? "secondary" : "outline"}>
                        {c.is_active ? "Active" : "Inactive"}
                      </Badge>
                    </TableCell>
                    <TableCell className="text-right">
                      <Button
                        size="icon"
                        variant="ghost"
                        onClick={() => {
                          setEditing(c);
                          setOpen(true);
                        }}
                      >
                        <Pencil className="h-4 w-4" />
                      </Button>
                      <Button
                        size="icon"
                        variant="ghost"
                        disabled={deactivate.isPending}
                        onClick={() => deactivate.mutate(c)}
                        title={c.is_active ? "Deactivate" : "Activate"}
                      >
                        <Power className="h-4 w-4" />
                      </Button>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </div>
      </div>
    </AppShell>
  );
}

function CouponDialog({
  editing,
  onSubmit,
  loading,
}: {
  editing: Coupon | null;
  onSubmit: (v: FormValues) => void;
  loading: boolean;
}) {
  const {
    register,
    handleSubmit,
    setValue,
    watch,
    formState: { errors },
  } = useForm<FormValues>({
    resolver: zodResolver(couponSchema),
    defaultValues: editing
      ? {
          code: editing.code,
          discount_type: editing.discount_type,
          discount_value: editing.discount_value,
          min_order_amount: editing.min_order_amount ?? undefined,
          max_uses: editing.max_uses ?? undefined,
          is_active: editing.is_active,
        }
      : { code: "", discount_type: "percent", discount_value: 10, is_active: true },
  });

  return (
    <DialogContent className="max-w-md">
      <DialogHeader>
        <DialogTitle>{editing ? "Edit coupon" : "New coupon"}</DialogTitle>
      </DialogHeader>
      <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
        <div className="space-y-1.5">
          <Label>Code</Label>
          <Input {...register("code")} placeholder="WELCOME10" className="uppercase" />
          {errors.code && <p className="text-xs text-destructive">{errors.code.message}</p>}
        </div>
        <div className="grid grid-cols-2 gap-4">
          <div className="space-y-1.5">
            <Label>Type</Label>
            <Select
              value={watch("discount_type")}
              onValueChange={(v) => setValue("discount_type", v as FormValues["discount_type"])}
            >
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="percent">Percent %</SelectItem>
                <SelectItem value="fixed">Fixed $</SelectItem>
              </SelectContent>
            </Select>
          </div>
          <div className="space-y-1.5">
            <Label>Value</Label>
            <Input
              type="number"
              step="0.01"
              {...register("discount_value", { valueAsNumber: true })}
            />
            {errors.discount_value && (
              <p className="text-xs text-destructive">{errors.discount_value.message}</p>
            )}
          </div>
        </div>
        <div className="grid grid-cols-2 gap-4">
          <div className="space-y-1.5">
            <Label>Min order ($)</Label>
            <Input
              type="number"
              step="0.01"
              {...register("min_order_amount", { valueAsNumber: true })}
              placeholder="None"
            />
          </div>
          <div className="space-y-1.5">
            <Label>Max uses</Label>
            <Input {...register("max_uses", { valueAsNumber: true })} placeholder="Unlimited" />
          </div>
        </div>
        <label className="flex items-center justify-between rounded-lg border border-border/60 px-3 py-2.5 text-sm">
          <span>Active</span>
          <Switch checked={watch("is_active")} onCheckedChange={(v) => setValue("is_active", v)} />
        </label>
        <Button type="submit" className="w-full" disabled={loading}>
          {loading ? "Saving…" : editing ? "Save changes" : "Create coupon"}
        </Button>
      </form>
    </DialogContent>
  );
}
