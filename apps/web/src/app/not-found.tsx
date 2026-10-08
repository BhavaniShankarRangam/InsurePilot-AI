import { Compass } from "lucide-react";
import Link from "next/link";

export default function NotFound() {
  return (
    <main id="main" className="grid min-h-dvh place-items-center px-6 text-center">
      <div>
        <Compass className="mx-auto size-10 text-accent" aria-hidden />
        <h1 className="mt-4 font-display text-3xl font-semibold">We couldn’t find that page</h1>
        <p className="mt-2 text-muted">It may have moved, or the link is out of date.</p>
        <Link href="/dashboard" className="bg-accent-gradient mt-6 inline-flex rounded-xl px-5 py-2.5 font-medium text-white">Go to my dashboard</Link>
      </div>
    </main>
  );
}
