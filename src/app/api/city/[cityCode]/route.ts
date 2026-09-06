import { cityCodeSchema, metricKeySchema } from "@/validations";
import { qCity } from "@/lib/queries";
import { z } from "zod";

const thresholdSchema = z.enum(["50", "100", "150"]).default("50");

export async function GET(req: Request, ctx: { params: Promise<{ cityCode: string }> }) {
  const { cityCode } = await ctx.params;
  const sp = new URL(req.url).searchParams;
  const keyRaw = sp.get("key") ?? undefined;
  const keyParsed = metricKeySchema.safeParse(keyRaw);
  if (!keyParsed.success) {
    return Response.json(
      { data: null, error: "invalid_key", message: "指标 key 非法（SO2/CO/NO2/O3_8h/PM10/PM2.5/AQI）" },
      { status: 400 }
    );
  }
  const thresholdRaw = sp.get("threshold") ?? undefined;
  const thresholdParsed = thresholdSchema.safeParse(thresholdRaw);
  if (!thresholdParsed.success) {
    return Response.json(
      { data: null, error: "invalid_threshold", message: "AQI 阈值非法（50/100/150）" },
      { status: 400 }
    );
  }
  const parsed = cityCodeSchema.safeParse(cityCode);
  if (!parsed.success) {
    return Response.json(
      { data: null, error: "invalid_cityCode", message: "城市编码非法" },
      { status: 400 }
    );
  }
  try {
    return Response.json({
      data: qCity(parsed.data, keyParsed.data, Number(thresholdParsed.data)),
      error: null,
      message: null,
    });
  } catch (e) {
    if (e instanceof Error && e.message.startsWith("no data for city")) {
      return Response.json(
        { data: null, error: "not_found", message: "未找到该城市数据" },
        { status: 404 }
      );
    }
    return Response.json(
      { data: null, error: "internal", message: String(e) },
      { status: 500 }
    );
  }
}
