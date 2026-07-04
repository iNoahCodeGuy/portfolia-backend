import { NextRequest, NextResponse } from 'next/server'

export const runtime = 'nodejs'
export const dynamic = 'force-dynamic'

type ChatRequest = {
  query: string
  role: string
  session_id: string
  chat_history: Array<{ role: string; content: string }>
}

export async function POST(request: NextRequest) {
  try {
    const body: ChatRequest = await request.json()

    // In production on Vercel, api/chat.py (Python serverless function) handles
    // /api/chat requests. This Next.js route is a fallback for local development
    // or if the Python function is unavailable.
    const pythonBackendUrl = process.env.PYTHON_BACKEND_URL || 'http://localhost:8000/chat'

    const response = await fetch(pythonBackendUrl, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body)
    })

    if (!response.ok) {
      throw new Error(`Backend returned ${response.status}`)
    }

    const data = await response.json()
    return NextResponse.json(data)

  } catch (error) {
    console.error('Chat API error:', error)
    return NextResponse.json(
      {
        success: false,
        answer: 'Something went wrong. Try again in a moment.',
        error: error instanceof Error ? error.message : 'Unknown error'
      },
      { status: 500 }
    )
  }
}
