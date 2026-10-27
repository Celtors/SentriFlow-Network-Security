-- Preserve v1 history/rules while adding dashboard, executable identity and observed-IP data.
ALTER TABLE flows ADD COLUMN updated_at TEXT;
ALTER TABLE flows ADD COLUMN process_key TEXT;
ALTER TABLE flows ADD COLUMN destination_ip TEXT;
ALTER TABLE flows ADD COLUMN state TEXT NOT NULL DEFAULT 'completed';
ALTER TABLE flows ADD COLUMN reason TEXT NOT NULL DEFAULT 'Recorded before dashboard integration';
ALTER TABLE flows ADD COLUMN deadline TEXT;
ALTER TABLE flows ADD COLUMN status_code INTEGER;
UPDATE flows SET updated_at=ts;
ALTER TABLE rules ADD COLUMN process_name TEXT;
UPDATE rules SET process_name=process_match;
