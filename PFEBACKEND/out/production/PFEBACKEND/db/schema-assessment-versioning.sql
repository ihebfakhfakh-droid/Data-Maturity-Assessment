-- Assessment versioning: colonne version + contrainte (client_id, year, version).
-- Compatible avec le schéma JPA singulier: assessment.

DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1
    FROM information_schema.columns
    WHERE table_schema = 'public'
      AND table_name = 'assessment'
      AND column_name = 'version'
  ) THEN
    ALTER TABLE assessment ADD COLUMN version integer NOT NULL DEFAULT 1;
  END IF;
END $$;

ALTER TABLE assessment ADD COLUMN IF NOT EXISTS submitted_by_id bigint;
ALTER TABLE assessment ADD COLUMN IF NOT EXISTS submitted_by_role varchar(32);

UPDATE assessment
SET submitted_by_id = client_id,
    submitted_by_role = 'CLIENT'
WHERE submitted_at IS NOT NULL
  AND submitted_by_id IS NULL;

DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_constraint WHERE conname = 'fk_assessment_submitted_by'
  ) THEN
    ALTER TABLE assessment
      ADD CONSTRAINT fk_assessment_submitted_by
      FOREIGN KEY (submitted_by_id) REFERENCES app_user(id);
  END IF;
END $$;

-- Ancienne unicité (client_id, year) seule — noms possibles (Hibernate / SQL manuel).
ALTER TABLE assessment DROP CONSTRAINT IF EXISTS uq_assessment_client_year;
ALTER TABLE assessment DROP CONSTRAINT IF EXISTS uq_assessments_client_year;
ALTER TABLE assessment DROP CONSTRAINT IF EXISTS assessments_client_id_year_key;

DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_constraint WHERE conname = 'uq_assessment_client_year_version'
  ) THEN
    ALTER TABLE assessment
      ADD CONSTRAINT uq_assessment_client_year_version UNIQUE (client_id, year, version);
  END IF;
END $$;
