"use client";

import { motion } from "framer-motion";
import { usePathname } from "next/navigation";
import * as React from "react";
import { Dialog, SheetContent } from "@/components/ui/overlay";
import { useAssistant } from "@/lib/store";
import { ChatPanel } from "./chat-panel";
import { Orb, orbLabel } from "./orb";

/** Floating AI Orb (available on every screen) that expands into the Command Center. */
export function CommandCenter() {
  const { open, setOpen, orb } = useAssistant();
  const pathname = usePathname();
  const onAssistantPage = pathname?.startsWith("/assistant");

  React.useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "j") {
        e.preventDefault();
        setOpen(!useAssistant.getState().open);
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [setOpen]);

  if (onAssistantPage) return null;

  return (
    <>
      <motion.button
        onClick={() => setOpen(true)}
        className="fixed bottom-24 right-5 z-40 rounded-full p-1 md:bottom-6 md:right-6"
        whileHover={{ scale: 1.06 }}
        whileTap={{ scale: 0.95 }}
        aria-label={`Open AI Command Center (${orbLabel(orb)}). Shortcut Ctrl+J`}
        initial={{ opacity: 0, scale: 0.6 }}
        animate={{ opacity: 1, scale: 1 }}
        transition={{ delay: 0.4, type: "spring", stiffness: 260, damping: 18 }}
      >
        <Orb state={orb} size={60} />
      </motion.button>
      <Dialog open={open} onOpenChange={setOpen}>
        <SheetContent title="AI Command Center">
          <ChatPanel />
        </SheetContent>
      </Dialog>
    </>
  );
}
