import { NextResponse, type NextRequest } from "next/server";

const SESSION_COOKIE = "ip_session";

// Optimistic check only — the API enforces real authorization on every request.
export function proxy(request: NextRequest) {
  const hasSession = request.cookies.has(SESSION_COOKIE);
  const { pathname, search } = request.nextUrl;

  if (!hasSession) {
    const url = new URL("/login", request.url);
    url.searchParams.set("next", pathname + search);
    return NextResponse.redirect(url);
  }
  return NextResponse.next();
}

export const config = {
  matcher: [
    "/dashboard/:path*",
    "/assistant/:path*",
    "/wallet/:path*",
    "/policies/:path*",
    "/claims/:path*",
    "/health/:path*",
    "/documents/:path*",
    "/compare/:path*",
    "/insights/:path*",
    "/universe/:path*",
    "/activity/:path*",
    "/privacy/:path*",
    "/settings/:path*",
    "/evaluations/:path*",
    "/onboarding/:path*",
  ],
};
