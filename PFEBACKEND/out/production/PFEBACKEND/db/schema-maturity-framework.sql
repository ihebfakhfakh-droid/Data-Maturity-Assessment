-- PostgreSQL: maturity framework columns + tables (idempotent).
-- Runs before Hibernate initializes the persistence unit when
-- spring.jpa.defer-datasource-initialization=true.
-- If questionnaire_segments does not exist yet, ALTER may fail: use spring.sql.init.continue-on-error=true.

CREATE TABLE IF NOT EXISTS maturity_framework_definitions (
    id                      BIGSERIAL PRIMARY KEY,
    code                    VARCHAR(80)  NOT NULL,
    name                    VARCHAR(200) NOT NULL,
    domain_scoring_method   VARCHAR(40)  NOT NULL,
    score_scale             VARCHAR(20)  NOT NULL,
    created_at              TIMESTAMPTZ  NOT NULL DEFAULT now(),
    CONSTRAINT uq_maturity_framework_code UNIQUE (code)
);

ALTER TABLE questionnaire_segments
    ADD COLUMN IF NOT EXISTS maturity_framework_id BIGINT;

ALTER TABLE questionnaire_segments
    ADD COLUMN IF NOT EXISTS parent_segment_id BIGINT;

CREATE TABLE IF NOT EXISTS project_custom_frameworks (
    project_id               BIGINT NOT NULL,
    maturity_framework_id    BIGINT NOT NULL,
    CONSTRAINT pk_project_custom_frameworks PRIMARY KEY (project_id, maturity_framework_id)
);
