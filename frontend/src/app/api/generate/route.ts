import { NextRequest, NextResponse } from 'next/server';

const ORCHESTRATOR_URL = process.env.ORCHESTRATOR_URL || 'http://localhost:8000';

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();

    const response = await fetch(`${ORCHESTRATOR_URL}/generate`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(body),
    });

    if (!response.ok) {
      throw new Error(`Orchestrator error: ${response.status}`);
    }

    const data = await response.json();
    return NextResponse.json(data);

  } catch (error) {
    console.error('API route error:', error);
    return NextResponse.json(
      { error: 'Failed to generate email' },
      { status: 500 }
    );
  }
}