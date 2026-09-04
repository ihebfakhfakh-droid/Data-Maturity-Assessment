-- Horodatage dernière saisie / dernière modification (historique).
-- Compatible avec le schéma JPA singulier: assessment_answer.

DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1
    FROM information_schema.columns
    WHERE table_schema = 'public'
      AND table_name = 'assessment_answer'
      AND column_name = 'answered_at'
  ) THEN
    ALTER TABLE assessment_answer ADD COLUMN answered_at timestamptz;
  END IF;
END $$;

UPDATE assessment_answer SET answered_at = NOW() WHERE answered_at IS NULL;

ALTER TABLE assessment_answer ALTER COLUMN answered_at SET DEFAULT NOW();

ALTER TABLE assessment_answer ALTER COLUMN answered_at SET NOT NULL;
