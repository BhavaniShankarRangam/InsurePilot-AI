"use client";

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MotionConfig } from "framer-motion";
import { ThemeProvider } from "next-themes";
import * as React from "react";
import { Toaster } from "sonner";
import { ApiError } from "@/lib/api";
import { hydrateUI, useUI } from "@/lib/store";

export function Providers({ children }: { children: React.ReactNode }) {
  const [client] = React.useState(
    () =>
      new QueryClient({
        defaultOptions: {
          queries: {
            staleTime: 20_000,
            refetchOnWindowFocus: false,
            retry: (count, err) => !(err instanceof ApiError && [401, 403, 404].includes(err.status)) && count < 2,
          },
        },
      }),
  );
  const reducedMotion = useUI((s) => s.reducedMotion);
  React.useEffect(() => hydrateUI(), []);

  return (
    <ThemeProvider attribute="class" defaultTheme="system" enableSystem disableTransitionOnChange>
      <QueryClientProvider client={client}>
        <MotionConfig reducedMotion={reducedMotion ? "always" : "user"}>{children}</MotionConfig>
        <Toaster position="bottom-right" richColors closeButton toastOptions={{ className: "!rounded-2xl" }} />
      </QueryClientProvider>
    </ThemeProvider>
  );
}
