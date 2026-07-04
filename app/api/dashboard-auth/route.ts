import { NextRequest, NextResponse } from 'next/server'
import {
  SESSION_COOKIE,
  SESSION_LIFETIME_MS,
  createSessionToken,
  passwordsMatch,
} from '@/lib/dashboard-auth'

export async function POST(request: NextRequest) {
  const correct = process.env.DASHBOARD_PASSWORD
  if (!correct) {
    return NextResponse.json(
      { error: 'Dashboard authentication is not configured' },
      { status: 503 }
    )
  }

  let password: unknown
  try {
    ;({ password } = await request.json())
  } catch {
    return NextResponse.json({ error: 'Invalid request body' }, { status: 400 })
  }

  if (typeof password !== 'string' || !(await passwordsMatch(password, correct))) {
    return NextResponse.json({ error: 'Wrong password' }, { status: 401 })
  }

  const response = NextResponse.json({ ok: true })
  response.cookies.set(SESSION_COOKIE, await createSessionToken(correct), {
    httpOnly: true,
    secure: process.env.NODE_ENV === 'production',
    sameSite: 'lax',
    path: '/',
    maxAge: SESSION_LIFETIME_MS / 1000,
  })
  return response
}
