-- Idempotent JPA/PostgreSQL synchronization.
-- This script is safe to run at every startup because every change uses IF NOT EXISTS
-- or preserves existing data while aligning column types/defaults with current entities.

ALTER TABLE sub_domain
    ADD COLUMN IF NOT EXISTS weight DOUBLE PRECISION DEFAULT 1;

ALTER TABLE sub_domain
    ALTER COLUMN weight TYPE DOUBLE PRECISION USING weight::DOUBLE PRECISION,
    ALTER COLUMN weight SET DEFAULT 1;

ALTER TABLE sub_domain
    ADD COLUMN IF NOT EXISTS code VARCHAR(80),
    ADD COLUMN IF NOT EXISTS maturity_framework_id BIGINT,
    ADD COLUMN IF NOT EXISTS parent_segment_id BIGINT;

ALTER TABLE assessment
    ADD COLUMN IF NOT EXISTS submitted_by_id BIGINT,
    ADD COLUMN IF NOT EXISTS submitted_by_role VARCHAR(32),
    ADD COLUMN IF NOT EXISTS version_comment VARCHAR(1000),
    ADD COLUMN IF NOT EXISTS recommendation_target_score DOUBLE PRECISION;

ALTER TABLE assessment_answer
    ADD COLUMN IF NOT EXISTS note VARCHAR(1000);

UPDATE assessment
SET submitted_by_id = client_id,
    submitted_by_role = 'CLIENT'
WHERE submitted_at IS NOT NULL
  AND submitted_by_id IS NULL;

DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'fk_assessment_submitted_by') THEN
    ALTER TABLE assessment
      ADD CONSTRAINT fk_assessment_submitted_by
      FOREIGN KEY (submitted_by_id) REFERENCES app_user(id)
      NOT VALID;
  END IF;
EXCEPTION WHEN others THEN
  RAISE NOTICE 'Skipping fk_assessment_submitted_by: %', SQLERRM;
END $$;
