-- Persist AI recommendation target score on each assessment version.
ALTER TABLE assessment
    ADD COLUMN IF NOT EXISTS recommendation_target_score DOUBLE PRECISION;
