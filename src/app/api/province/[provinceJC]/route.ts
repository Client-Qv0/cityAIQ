import { provinceJCSchema } from "@/validations";
import { parseProvinceJC } from "@/lib/jc";
import { qProvince } from "@/lib/queries";

export async function GET(_req: Request, ctx: { params: Promise<{ provinceJC: string }> }) {
  const { provinceJC } = await ctx.params;
  const parsed = provinceJCSchema.safeParse(provinceJC);
  if (!parsed.success) {
    return Response.json(
      { data: null, error: "invalid_provinceJC", message: "省份简称非法" },
      { status: 400 }
    );
  }
  const ref = parseProvinceJC(parsed.data);
  if (!ref) {
    return Response.json(
      { data: null, error: "not_found", message: "未找到该省份" },
      { status: 404 }
    );
  }
  try {
    return Response.json({ data: qProvince(ref.provinceCode), error: null, message: null });
  } catch (e) {
    return Response.json(
      { data: null, error: "internal", message: String(e) },
      { status: 500 }
    );
  }
}
