import { CommandCenter } from "@/components/ai/command-center";
import { CommandPalette } from "@/components/shell/command-palette";
import { MobileNav, Sidebar } from "@/components/shell/sidebar";
import { Topbar } from "@/components/shell/topbar";

export default function PlatformLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="relative flex min-h-dvh">
      <div className="ambient" aria-hidden />
      <Sidebar />
      <div className="relative z-10 flex min-w-0 flex-1 flex-col">
        <Topbar />
        <main id="main" className="mx-auto w-full max-w-[1320px] flex-1 px-4 pb-32 pt-8 md:px-8 md:pb-16">
          {children}
        </main>
      </div>
      <MobileNav />
      <CommandCenter />
      <CommandPalette />
    </div>
  );
}
