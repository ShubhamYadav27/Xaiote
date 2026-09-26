import { NextResponse } from 'next/server';
import type { NextRequest } from 'next/server';

/**
 * Next.js Edge Middleware — Route Protection
 *
 * Protects all dashboard routes (routes under /(dashboard)/ group).
 * Since the (dashboard) route group resolves to paths like /customers, /vendors, etc.,
 * we match those paths explicitly.
 *
 * NOTE: This is a client-side convenience check only.
 * The backend independently enforces authorization via JWT validation on every API call.
 * This middleware prevents the dashboard UI from flashing before redirect.
 *
 * We check for the access_token cookie. Since the app uses localStorage,
 * we set a lightweight 'xaiote_auth' cookie from the client side as a signal.
 */

const PROTECTED_PATHS = [
  '/customers',
  '/vendors',
  '/products',
  '/machines',
  '/work-orders',
  '/imports',
];

export function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl;

  // Check if this is a protected dashboard path
  const isProtected = PROTECTED_PATHS.some(
    (p) => pathname === p || pathname.startsWith(p + '/')
  );

  if (!isProtected) {
    return NextResponse.next();
  }

  // Check for auth signal cookie (set by client-side auth flow)
  const authCookie = request.cookies.get('xaiote_auth');
  if (!authCookie?.value) {
    const loginUrl = new URL('/login', request.url);
    loginUrl.searchParams.set('redirect', pathname);
    return NextResponse.redirect(loginUrl);
  }

  return NextResponse.next();
}

export const config = {
  matcher: [
    '/customers/:path*',
    '/vendors/:path*',
    '/products/:path*',
    '/machines/:path*',
    '/work-orders/:path*',
    '/imports/:path*',
  ],
};
