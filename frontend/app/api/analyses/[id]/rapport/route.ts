import { NextRequest, NextResponse } from "next/server";

const BACKEND_URL = process.env.BACKEND_URL ?? "http://localhost:8000";

export async function GET(
  req: NextRequest,
  { params }: { params: { id: string } }
) {
  const format = req.nextUrl.searchParams.get("format") ?? "pdf";

  try {
    const res = await fetch(
      `${BACKEND_URL}/analyses/${params.id}/rapport?format=${format}`,
      { cache: "no-store" }
    );

    if (!res.ok) {
      const text = await res.text();
      return NextResponse.json({ detail: text }, { status: res.status });
    }

    // Streaming : transmettre le body binaire tel quel avec les headers du backend
    const body = await res.arrayBuffer();
    const contentType = res.headers.get("content-type") ?? "application/octet-stream";
    const disposition = res.headers.get("content-disposition") ?? "";

    return new NextResponse(body, {
      status: 200,
      headers: {
        "Content-Type": contentType,
        ...(disposition ? { "Content-Disposition": disposition } : {}),
      },
    });
  } catch {
    return NextResponse.json(
      { detail: "Impossible de joindre le backend FastAPI." },
      { status: 502 }
    );
  }
}
