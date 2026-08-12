import { NextResponse } from "next/server";
import sqlite3 from "sqlite3";
import path from "path";

// Initialize DB connection
// Using path.join to point to backend/agent_data.db from the frontend app
const dbPath = path.join(process.cwd(), "..", "backend", "agent_data.db");

export async function GET() {
  return new Promise((resolve) => {
    const db = new sqlite3.Database(dbPath, sqlite3.OPEN_READONLY, (err) => {
      if (err) {
        console.error("Database connection error:", err);
        return resolve(NextResponse.json({ error: "Failed to connect to database" }, { status: 500 }));
      }
    });

    const query = `
      SELECT ticket_id, customer_name, issue_summary, urgency, created_at 
      FROM tickets 
      ORDER BY created_at DESC
    `;

    db.all(query, [], (err, rows) => {
      db.close();
      if (err) {
        console.error("Query error:", err);
        return resolve(NextResponse.json({ error: "Failed to query database" }, { status: 500 }));
      }
      return resolve(NextResponse.json({ tickets: rows }));
    });
  });
}
