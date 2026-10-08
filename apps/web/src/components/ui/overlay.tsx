"use client";

import * as DialogPrimitive from "@radix-ui/react-dialog";
import * as SwitchPrimitive from "@radix-ui/react-switch";
import * as TabsPrimitive from "@radix-ui/react-tabs";
import { X } from "lucide-react";
import * as React from "react";
import { cn } from "@/lib/utils";

/* ---------------- Dialog ---------------- */
export const Dialog = DialogPrimitive.Root;
export const DialogTrigger = DialogPrimitive.Trigger;
export const DialogClose = DialogPrimitive.Close;

export function DialogContent({ className, children, title, description, wide, onOpenAutoFocus }: { className?: string; children: React.ReactNode; title: string; description?: string; wide?: boolean; onOpenAutoFocus?: (e: Event) => void }) {
  return (
    <DialogPrimitive.Portal>
      <DialogPrimitive.Overlay className="fixed inset-0 z-50 bg-black/40 backdrop-blur-sm data-[state=open]:animate-in data-[state=open]:fade-in" />
      <DialogPrimitive.Content
        onOpenAutoFocus={onOpenAutoFocus}
        className={cn(
          "glass-strong fixed left-1/2 top-1/2 z-50 max-h-[88vh] w-[calc(100%-2rem)] -translate-x-1/2 -translate-y-1/2 overflow-y-auto rounded-3xl p-6 focus:outline-none",
          wide ? "max-w-3xl" : "max-w-lg",
          className,
        )}
      >
        <div className="mb-4 flex items-start justify-between gap-4">
          <div>
            <DialogPrimitive.Title className="font-display text-lg font-semibold">{title}</DialogPrimitive.Title>
            {description ? (
              <DialogPrimitive.Description className="mt-1 text-sm text-muted">{description}</DialogPrimitive.Description>
            ) : (
              <DialogPrimitive.Description className="sr-only">{title}</DialogPrimitive.Description>
            )}
          </div>
          <DialogPrimitive.Close className="rounded-lg p-1.5 text-muted hover:bg-surface-hover hover:text-fg" aria-label="Close">
            <X className="size-4" />
          </DialogPrimitive.Close>
        </div>
        {children}
      </DialogPrimitive.Content>
    </DialogPrimitive.Portal>
  );
}

/* ---------------- Sheet (side panel) ---------------- */
export function SheetContent({ children, title, side = "right", className }: { children: React.ReactNode; title: string; side?: "right" | "bottom"; className?: string }) {
  return (
    <DialogPrimitive.Portal>
      <DialogPrimitive.Overlay className="fixed inset-0 z-50 bg-black/30 backdrop-blur-[2px]" />
      <DialogPrimitive.Content
        aria-describedby={undefined}
        className={cn(
          "glass-strong fixed z-50 flex flex-col focus:outline-none",
          side === "right" ? "inset-y-2 right-2 w-[min(560px,calc(100%-1rem))] rounded-3xl" : "inset-x-0 bottom-0 max-h-[92vh] rounded-t-3xl",
          className,
        )}
      >
        <DialogPrimitive.Title className="sr-only">{title}</DialogPrimitive.Title>
        {children}
      </DialogPrimitive.Content>
    </DialogPrimitive.Portal>
  );
}

/* ---------------- Tabs ---------------- */
export const Tabs = TabsPrimitive.Root;
export function TabsList({ className, ...props }: React.ComponentProps<typeof TabsPrimitive.List>) {
  return <TabsPrimitive.List className={cn("glass inline-flex flex-wrap gap-1 rounded-2xl p-1", className)} {...props} />;
}
export function TabsTrigger({ className, ...props }: React.ComponentProps<typeof TabsPrimitive.Trigger>) {
  return (
    <TabsPrimitive.Trigger
      className={cn(
        "rounded-xl px-3.5 py-1.5 text-sm text-muted transition-all hover:text-fg data-[state=active]:bg-surface-strong data-[state=active]:text-fg data-[state=active]:shadow-soft",
        className,
      )}
      {...props}
    />
  );
}
export const TabsContent = ({ className, ...props }: React.ComponentProps<typeof TabsPrimitive.Content>) => (
  <TabsPrimitive.Content className={cn("mt-6 focus:outline-none", className)} {...props} />
);

/* ---------------- Switch ---------------- */
export function Switch({ checked, onCheckedChange, label, id }: { checked: boolean; onCheckedChange: (v: boolean) => void; label: string; id?: string }) {
  return (
    <SwitchPrimitive.Root
      id={id}
      checked={checked}
      onCheckedChange={onCheckedChange}
      aria-label={label}
      className="relative h-6 w-11 shrink-0 rounded-full bg-surface-hover ring-1 ring-border-strong transition-colors data-[state=checked]:bg-accent"
    >
      <SwitchPrimitive.Thumb className="block size-5 translate-x-0.5 rounded-full bg-white shadow transition-transform data-[state=checked]:translate-x-[22px]" />
    </SwitchPrimitive.Root>
  );
}

/* ---------------- Inputs ---------------- */
export const Input = React.forwardRef<HTMLInputElement, React.InputHTMLAttributes<HTMLInputElement>>(({ className, ...props }, ref) => (
  <input
    ref={ref}
    className={cn(
      "h-11 w-full rounded-xl border border-border bg-surface px-3.5 text-sm text-fg placeholder:text-subtle transition-colors focus:border-accent focus:outline-none focus:ring-4 focus:ring-accent-soft",
      className,
    )}
    {...props}
  />
));
Input.displayName = "Input";

export const Textarea = React.forwardRef<HTMLTextAreaElement, React.TextareaHTMLAttributes<HTMLTextAreaElement>>(({ className, ...props }, ref) => (
  <textarea
    ref={ref}
    className={cn(
      "w-full rounded-xl border border-border bg-surface px-3.5 py-3 text-sm text-fg placeholder:text-subtle transition-colors focus:border-accent focus:outline-none focus:ring-4 focus:ring-accent-soft",
      className,
    )}
    {...props}
  />
));
Textarea.displayName = "Textarea";

export function Field({ label, error, children, htmlFor, hint }: { label: string; error?: string; children: React.ReactNode; htmlFor: string; hint?: string }) {
  return (
    <div className="space-y-1.5">
      <label htmlFor={htmlFor} className="text-sm font-medium">
        {label}
      </label>
      {children}
      {hint && !error && <p className="text-xs text-subtle">{hint}</p>}
      {error && (
        <p role="alert" className="text-xs text-danger">
          {error}
        </p>
      )}
    </div>
  );
}
