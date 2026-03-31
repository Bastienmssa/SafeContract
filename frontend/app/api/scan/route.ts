import { NextRequest, NextResponse } from "next/server";

const BACKEND_URL = process.env.BACKEND_URL ?? "http://localhost:8000";

export async function POST(req: NextRequest) {
  const formData = await req.formData();

  let backendRes: Response;
  try {
    backendRes = await fetch(`${BACKEND_URL}/scan`, {
      method: "POST",
      body: formData,
    });
  } catch {
    return NextResponse.json(
      { detail: "Impossible de joindre le backend FastAPI." },
      { status: 502 }
    );
  }

  const text = await backendRes.text();

  if (!text) {
    return NextResponse.json(
      { detail: `Le backend a renvoyé une réponse vide (HTTP ${backendRes.status}).` },
      { status: backendRes.status || 502 }
    );
  }

  let json: unknown;
  try {
    json = JSON.parse(text);
  } catch {
    return NextResponse.json(
      { detail: `Réponse non-JSON du backend : ${text.slice(0, 200)}` },
      { status: 502 }
    );
  }

  return NextResponse.json(json, { status: backendRes.status });
}
