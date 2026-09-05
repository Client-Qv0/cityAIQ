import { qNational } from "@/lib/queries";

export async function GET() {
  try {
    return Response.json({ data: qNational(), error: null, message: null });
  } catch (e) {
    return Response.json(
      { data: null, error: "internal", message: String(e) },
      { status: 500 }
    );
  }
}
