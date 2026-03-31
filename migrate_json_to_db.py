"""
Guardian AI — Database Migration Script
=======================================
Reads all incident Reports (*_incident_*.json) from the /artifacts folder
and seeds them into the new SQLAlchemy SQLite database (`guardian.db`).
Run this once when upgrading to Phase 3.
"""

import os
import json
from pathlib import Path
from datetime import datetime, timezone
import dateutil.parser

from app.database import engine, Base, SessionLocal
from app.models import Incident

ARTIFACTS_DIR = Path("artifacts")

def run_migration():
    print("⏳ Starting migration from JSON /artifacts -> SQLite database...")
    
    # 1. Create the database tables
    Base.metadata.create_all(bind=engine)
    print("✅ Database tables created (guardian.db).")

    if not ARTIFACTS_DIR.exists():
        print("⏭️ No /artifacts folder found. Nothing to migrate.")
        return

    json_files = list(ARTIFACTS_DIR.glob("*_incident_*.json"))
    if not json_files:
        print("⏭️ No incident JSON files found in /artifacts. Nothing to migrate.")
        return

    db = SessionLocal()
    migrated_count = 0
    skipped_count = 0

    for file_path in json_files:
        try:
            data = json.loads(file_path.read_text(encoding="utf-8"))
            
            # Use dateteutil parser for flexible ISO parsing
            ts_str = data.get("timestamp")
            if ts_str:
                ts = dateutil.parser.isoparse(ts_str)
            else:
                ts = datetime.now(timezone.utc)

            fb_at_str = data.get("feedback_at")
            fb_at = dateutil.parser.isoparse(fb_at_str) if fb_at_str else None

            # Create Incident Model
            incident = Incident(
                timestamp=ts,
                user_id=data.get("user", "Unknown"),
                channel=data.get("channel", "Unknown"),
                slack_message=data.get("slack_message", ""),
                ai_reasoning=data.get("ai_reasoning", ""),
                severity=data.get("severity", 0),
                detected_by=data.get("detected_by", "ai"),
                type=data.get("type", "system"),
                github_confirmed=data.get("github_confirmed", False),
                github_evidence=data.get("github_evidence", []),
                github_url=data.get("github_url"),
                user_feedback=data.get("user_feedback"),
                feedback_by=data.get("feedback_by"),
                feedback_at=fb_at,
                policy_url=data.get("policy_url")
            )

            db.add(incident)
            migrated_count += 1
            
        except Exception as e:
            print(f"❌ Failed to parse/migrate {file_path.name}: {e}")
            skipped_count += 1

    try:
        db.commit()
        print(f"🎉 Migration Complete: {migrated_count} records inserted successfully.")
        if skipped_count > 0:
            print(f"⚠️  Skipped {skipped_count} invalid files.")
    except Exception as e:
        db.rollback()
        print(f"❌ Database commit failed: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    run_migration()
