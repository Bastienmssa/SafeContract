import { NextResponse } from "next/server";

const BACKEND_URL = process.env.BACKEND_URL ?? "http://localhost:8000";

export async function GET() {
  try {
    const res = await fetch(`${BACKEND_URL}/analyses`, { cache: "no-store" });
    const json = await res.json();
    return NextResponse.json(json, { status: res.status });
  } catch {
    return NextResponse.json({ detail: "Impossible de joindre le backend FastAPI." }, { status: 502 });
  }
}
