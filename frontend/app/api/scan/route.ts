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

  const json = await backendRes.json();
  return NextResponse.json(json, { status: backendRes.status });
}
