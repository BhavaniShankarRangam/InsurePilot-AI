"use client";

import * as React from "react";
import { type PageContext, useAssistant } from "./store";

/** Tells the AI assistant what the user is looking at, so questions are understood in context. */
export function usePageContext(ctx: PageContext) {
  const setPage = useAssistant((s) => s.setPage);
  const key = JSON.stringify(ctx);
  React.useEffect(() => {
    setPage(JSON.parse(key));
  }, [key, setPage]);
}
