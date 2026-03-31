import { NextResponse } from "next/server";

const BACKEND_URL = process.env.BACKEND_URL ?? "http://localhost:8000";

export async function GET() {
  let res: Response;
  try {
    res = await fetch(`${BACKEND_URL}/analyses`, { cache: "no-store" });
  } catch {
    return NextResponse.json({ detail: "Impossible de joindre le backend FastAPI." }, { status: 502 });
  }

  const text = await res.text();
  if (!text) return NextResponse.json([], { status: 200 });

  try {
    return NextResponse.json(JSON.parse(text), { status: res.status });
  } catch {
    return NextResponse.json({ detail: `Réponse non-JSON du backend : ${text.slice(0, 200)}` }, { status: 502 });
  }
}
