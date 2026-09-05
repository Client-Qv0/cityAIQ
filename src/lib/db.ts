import Database from "better-sqlite3";
import path from "path";

export const DB_PATH = path.join(process.cwd(), "prisma", "weather.db");
export const db = new Database(DB_PATH, { readonly: true });
