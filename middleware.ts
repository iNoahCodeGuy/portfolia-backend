import { NextRequest, NextResponse } from 'next/server'
import { SESSION_COOKIE, verifySessionToken } from './lib/dashboard-auth'

/**
 * Protects /dashboard and /api/analytics behind a signed session cookie.
 * Fails closed: if DASHBOARD_PASSWORD is not configured, protected routes
 * return 503 instead of becoming public.
 */
export async function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl

  // The login page and login API stay reachable
  if (pathname === '/dashboard/login' || pathname === '/api/dashboard-auth') {
    return NextResponse.next()
  }

  const password = process.env.DASHBOARD_PASSWORD
  if (!password) {
    return new NextResponse('Dashboard authentication is not configured', { status: 503 })
  }

  const token = request.cookies.get(SESSION_COOKIE)?.value
  if (await verifySessionToken(token, password)) {
    return NextResponse.next()
  }

  if (pathname.startsWith('/api/')) {
    return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
  }
  return NextResponse.redirect(new URL('/dashboard/login', request.url))
}

export const config = {
  matcher: ['/dashboard/:path*', '/api/analytics/:path*'],
}
