import Link from "next/link";
import { Logo } from "@/components/brand/logo";

export default function AuthLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="relative grid min-h-dvh place-items-center px-4 py-12">
      <div className="ambient" aria-hidden />
      <div className="grid-bg pointer-events-none fixed inset-0" aria-hidden />
      <main id="main" className="relative z-10 w-full max-w-md">
        <Link href="/" className="mb-8 flex justify-center" aria-label="InsurePilot home"><Logo /></Link>
        {children}
      </main>
    </div>
  );
}
