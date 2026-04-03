import { NextRequest, NextResponse } from "next/server";

const BACKEND_URL = process.env.BACKEND_URL ?? "http://localhost:8000";

export async function GET() {
  try {
    const res = await fetch(`${BACKEND_URL}/scan/status`);
    const data = await res.json();
    return NextResponse.json(data, { status: res.status });
  } catch {
    // Si le backend est injoignable, on suppose qu'aucun scan n'est en cours
    return NextResponse.json({ scanning: false });
  }
}

export async function POST(req: NextRequest) {
  const formData = await req.formData();

  let backendRes: Response;
  try {
    backendRes = await fetch(`${BACKEND_URL}/scan`, {
      method: "POST",
      body: formData,
      signal: AbortSignal.timeout(600_000), // 10 min — Mythril + GNN peuvent être lents
    });
  } catch (err) {
    const isTimeout = err instanceof Error && err.name === "TimeoutError";
    return NextResponse.json(
      { detail: isTimeout ? "L'analyse a dépassé le délai maximal (10 min)." : "Impossible de joindre le backend FastAPI." },
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
