"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useQueryClient } from "@tanstack/react-query";
import { Lock, Sparkles } from "lucide-react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import * as React from "react";
import { useForm } from "react-hook-form";
import { z } from "zod";
import { Button } from "@/components/ui/button";
import { Field, Input } from "@/components/ui/overlay";
import { Card } from "@/components/ui/primitives";
import { api, ApiError } from "@/lib/api";
import type { User } from "@/lib/types";

const loginSchema = z.object({
  email: z.string().email("Enter a valid email"),
  password: z.string().min(1, "Enter your password"),
});
const signupSchema = z.object({
  full_name: z.string().min(1, "Tell us your name").max(120),
  email: z.string().email("Enter a valid email"),
  password: z
    .string()
    .min(10, "Use at least 10 characters")
    .refine((v) => /[^a-zA-Z]/.test(v) && /[a-zA-Z]/.test(v), "Mix letters with numbers or symbols"),
});

type Mode = "login" | "signup";

function safeNext(n: string | null) {
  return n && n.startsWith("/") && !n.startsWith("//") ? n : "/dashboard";
}

export function AuthForm({ mode }: { mode: Mode }) {
  const router = useRouter();
  const params = useSearchParams();
  const qc = useQueryClient();
  const [error, setError] = React.useState<string | null>(null);
  const [demoLoading, setDemoLoading] = React.useState(false);
  const schema = mode === "login" ? loginSchema : signupSchema;
  const form = useForm<z.infer<typeof signupSchema>>({ resolver: zodResolver(schema as typeof signupSchema), defaultValues: { email: "", password: "", full_name: "" } });

  const done = (u: User) => {
    qc.setQueryData(["me"], u);
    router.push(mode === "signup" || !u.onboarding_complete ? "/onboarding" : safeNext(params.get("next")));
  };

  const onSubmit = form.handleSubmit(async (values) => {
    setError(null);
    try {
      const res = await api.post<{ user: User }>(mode === "login" ? "/auth/login" : "/auth/register", values);
      done(res.user);
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Something went wrong");
    }
  });

  const demo = async () => {
    setDemoLoading(true);
    try {
      const res = await api.post<{ user: User }>("/auth/demo");
      qc.setQueryData(["me"], res.user);
      router.push(safeNext(params.get("next")));
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "The demo is unavailable — is the API running?");
      setDemoLoading(false);
    }
  };

  const errs = form.formState.errors;
  return (
    <Card className="p-7">
      <h1 className="font-display text-2xl font-semibold tracking-tight">{mode === "login" ? "Welcome back" : "Create your account"}</h1>
      <p className="mt-1 text-sm text-muted">{mode === "login" ? "Sign in to your insurance co-pilot." : "Set up takes less than five minutes."}</p>

      <Button onClick={demo} loading={demoLoading} className="mt-6 w-full" size="lg">
        <Sparkles /> Explore the live demo
      </Button>
      <p className="mt-2 text-center text-xs text-subtle">Synthetic profile · no real data · full product</p>

      <div className="my-6 flex items-center gap-3 text-xs text-subtle"><span className="h-px flex-1 bg-border" /> or <span className="h-px flex-1 bg-border" /></div>

      <form onSubmit={onSubmit} className="space-y-4" noValidate>
        {mode === "signup" && (
          <Field label="Full name" htmlFor="full_name" error={errs.full_name?.message}>
            <Input id="full_name" autoComplete="name" aria-invalid={!!errs.full_name} {...form.register("full_name")} />
          </Field>
        )}
        <Field label="Email" htmlFor="email" error={errs.email?.message}>
          <Input id="email" type="email" autoComplete="email" aria-invalid={!!errs.email} {...form.register("email")} />
        </Field>
        <Field label="Password" htmlFor="password" error={errs.password?.message} hint={mode === "signup" ? "At least 10 characters, mixing letters with numbers or symbols" : undefined}>
          <Input id="password" type="password" autoComplete={mode === "login" ? "current-password" : "new-password"} aria-invalid={!!errs.password} {...form.register("password")} />
        </Field>
        {error && <p role="alert" className="rounded-xl bg-danger-soft px-3 py-2 text-sm text-danger">{error}</p>}
        <Button type="submit" variant="secondary" className="w-full" loading={form.formState.isSubmitting}>
          {mode === "login" ? "Sign in" : "Create account"}
        </Button>
      </form>
      <p className="mt-6 text-center text-sm text-muted">
        {mode === "login" ? "New to InsurePilot? " : "Already have an account? "}
        <Link href={mode === "login" ? "/signup" : "/login"} className="font-medium text-accent hover:underline">{mode === "login" ? "Create an account" : "Sign in"}</Link>
      </p>
      <p className="mt-4 flex items-center justify-center gap-1.5 text-xs text-subtle"><Lock className="size-3" aria-hidden /> Encrypted session · we never sell your data</p>
    </Card>
  );
}
