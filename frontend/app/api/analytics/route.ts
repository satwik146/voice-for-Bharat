import { NextResponse } from "next/server";
import sqlite3 from "sqlite3";
import path from "path";

const dbPath = path.join(process.cwd(), "..", "backend", "agent_data.db");

export async function GET() {
  return new Promise((resolve) => {
    const db = new sqlite3.Database(dbPath, sqlite3.OPEN_READONLY, (err) => {
      if (err) {
        console.error("Database connection error:", err);
        return resolve(NextResponse.json({ error: "Failed to connect to database" }, { status: 500 }));
      }
    });

    const queries = {
      total: "SELECT COUNT(*) as count FROM call_log",
      successful: "SELECT COUNT(*) as count FROM call_log WHERE outcome = 'Successful'",
      failed: "SELECT COUNT(*) as count FROM call_log WHERE outcome = 'Failed'",
      recent: "SELECT id, contact, name, outcome, detail, created_at FROM call_log ORDER BY created_at DESC LIMIT 10",
      daily: `
        SELECT 
          SUBSTR(created_at, 1, 10) as date, 
          COUNT(*) as total, 
          SUM(CASE WHEN outcome='Successful' THEN 1 ELSE 0 END) as successful,
          SUM(CASE WHEN outcome='Failed' THEN 1 ELSE 0 END) as failed
        FROM call_log
        GROUP BY SUBSTR(created_at, 1, 10)
        ORDER BY date ASC
        LIMIT 14
      `
    };

    const results: any = {
      total_calls: 0,
      successful_calls: 0,
      failed_calls: 0,
      recent_calls: [],
      daily_activity: []
    };

    // Run queries sequentially
    db.get(queries.total, [], (err, row: any) => {
      if (!err && row) results.total_calls = row.count;

      db.get(queries.successful, [], (err, row: any) => {
        if (!err && row) results.successful_calls = row.count;

        db.get(queries.failed, [], (err, row: any) => {
          if (!err && row) results.failed_calls = row.count;
          
          db.all(queries.recent, [], (err, rows: any) => {
            if (!err && rows) results.recent_calls = rows;

            db.all(queries.daily, [], (err, rows: any) => {
               if (!err && rows) results.daily_activity = rows;

               db.close();
               return resolve(NextResponse.json(results));
            });
          });
        });
      });
    });
  });
}
