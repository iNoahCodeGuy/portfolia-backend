/**
 * Dashboard session auth.
 *
 * The cookie never contains the password itself — it holds an expiring token
 * signed with HMAC-SHA256, so a leaked cookie can't reveal the secret and
 * tokens stop working after SESSION_LIFETIME_MS. Uses the Web Crypto API so
 * the same code runs in Edge middleware and Node route handlers.
 */

export const SESSION_COOKIE = 'dashboard_session'
export const SESSION_LIFETIME_MS = 30 * 24 * 60 * 60 * 1000 // 30 days

const encoder = new TextEncoder()

async function hmacHex(secret: string, message: string): Promise<string> {
  const key = await crypto.subtle.importKey(
    'raw',
    encoder.encode(secret),
    { name: 'HMAC', hash: 'SHA-256' },
    false,
    ['sign']
  )
  const signature = await crypto.subtle.sign('HMAC', key, encoder.encode(message))
  return toHex(signature)
}

async function sha256Hex(value: string): Promise<string> {
  return toHex(await crypto.subtle.digest('SHA-256', encoder.encode(value)))
}

function toHex(buffer: ArrayBuffer): string {
  return Array.from(new Uint8Array(buffer))
    .map(b => b.toString(16).padStart(2, '0'))
    .join('')
}

function timingSafeEqual(a: string, b: string): boolean {
  if (a.length !== b.length) return false
  let diff = 0
  for (let i = 0; i < a.length; i++) {
    diff |= a.charCodeAt(i) ^ b.charCodeAt(i)
  }
  return diff === 0
}

export async function createSessionToken(secret: string): Promise<string> {
  const expires = Date.now() + SESSION_LIFETIME_MS
  const signature = await hmacHex(secret, `dashboard-session:${expires}`)
  return `${expires}.${signature}`
}

export async function verifySessionToken(
  token: string | undefined,
  secret: string
): Promise<boolean> {
  if (!token) return false
  const dot = token.indexOf('.')
  if (dot < 1) return false
  const expires = Number(token.slice(0, dot))
  if (!Number.isFinite(expires) || Date.now() > expires) return false
  const expected = await hmacHex(secret, `dashboard-session:${expires}`)
  return timingSafeEqual(token.slice(dot + 1), expected)
}

/** Constant-time password check: hashing both sides first fixes the length. */
export async function passwordsMatch(submitted: string, correct: string): Promise<boolean> {
  const [a, b] = await Promise.all([sha256Hex(submitted), sha256Hex(correct)])
  return timingSafeEqual(a, b)
}
