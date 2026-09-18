-- Non destructive recovery for the legacy singular PostgreSQL schema.
-- This file is intentionally idempotent: it can run at every backend startup.

CREATE TABLE IF NOT EXISTS app_user (
    id BIGSERIAL PRIMARY KEY,
    full_name VARCHAR(120),
    email VARCHAR(160),
    password TEXT,
    role VARCHAR(32),
    managed_by_id BIGINT,
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS project (
    id BIGSERIAL PRIMARY KEY,
    client_id BIGINT,
    name VARCHAR(200),
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS framework (
    id BIGSERIAL PRIMARY KEY,
    name VARCHAR(100),
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS project_framework (
    project_id BIGINT,
    framework_id BIGINT,
    assigned_at TIMESTAMPTZ DEFAULT now(),
    PRIMARY KEY (project_id, framework_id)
);

CREATE TABLE IF NOT EXISTS project_consultants (
    project_id BIGINT,
    consultant_id BIGINT,
    can_manage_project BOOLEAN DEFAULT FALSE,
    assigned_at TIMESTAMPTZ DEFAULT now(),
    PRIMARY KEY (project_id, consultant_id)
);

CREATE TABLE IF NOT EXISTS domain (
    id BIGSERIAL PRIMARY KEY,
    code VARCHAR(80),
    title VARCHAR(240),
    sort_order INTEGER DEFAULT 0,
    weight NUMERIC(10, 2),
    active BOOLEAN DEFAULT TRUE,
    framework_id BIGINT,
    parent_segment_id BIGINT
);

CREATE TABLE IF NOT EXISTS sub_domain (
    id BIGSERIAL PRIMARY KEY,
    domain_id BIGINT,
    name VARCHAR(200),
    sort_order INTEGER DEFAULT 0,
    weight NUMERIC(10, 2)
);

CREATE TABLE IF NOT EXISTS question (
    id BIGSERIAL PRIMARY KEY,
    domain_id BIGINT,
    code VARCHAR(120),
    text TEXT,
    sort_order INTEGER DEFAULT 0,
    active BOOLEAN DEFAULT TRUE,
    sub_domain_id BIGINT,
    weight NUMERIC(10, 2)
);

CREATE TABLE IF NOT EXISTS assessment (
    id BIGSERIAL PRIMARY KEY,
    client_id BIGINT NOT NULL,
    project_id BIGINT,
    year INTEGER NOT NULL,
    version INTEGER NOT NULL DEFAULT 1,
    status VARCHAR(20) NOT NULL DEFAULT 'DRAFT',
    is_submitted BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    submitted_at TIMESTAMPTZ,
    CONSTRAINT uq_assessment_client_year_version UNIQUE (client_id, year, version)
);

CREATE TABLE IF NOT EXISTS assessment_answer (
    id BIGSERIAL PRIMARY KEY,
    assessment_id BIGINT,
    question_id BIGINT,
    score INTEGER DEFAULT 0,
    note VARCHAR(1000),
    answered_at TIMESTAMPTZ DEFAULT now(),
    evidence_staff_rating VARCHAR(20),
    evidence_rated_by_id BIGINT,
    evidence_rated_at TIMESTAMPTZ,
    evidence_staff_comment VARCHAR(1000),
    project_id BIGINT,
    is_submitted BOOLEAN DEFAULT FALSE,
    submitted_at TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS evidence (
    id BIGSERIAL PRIMARY KEY,
    uploaded_by_id BIGINT,
    storage_path TEXT,
    original_file_name VARCHAR(255),
    created_at TIMESTAMPTZ DEFAULT now(),
    answer_id BIGINT,
    staff_rating VARCHAR(20),
    rated_by_id BIGINT
);

ALTER TABLE app_user
    ADD COLUMN IF NOT EXISTS full_name VARCHAR(120),
    ADD COLUMN IF NOT EXISTS email VARCHAR(160),
    ADD COLUMN IF NOT EXISTS password TEXT,
    ADD COLUMN IF NOT EXISTS role VARCHAR(32),
    ADD COLUMN IF NOT EXISTS managed_by_id BIGINT,
    ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ DEFAULT now();

DO $$
BEGIN
  IF EXISTS (
    SELECT 1
    FROM information_schema.columns
    WHERE table_name = 'app_user'
      AND column_name = 'assigned_consultant_id'
  ) THEN
    EXECUTE $copy$
      INSERT INTO project_consultants (project_id, consultant_id, can_manage_project, assigned_at)
      SELECT p.id, c.assigned_consultant_id, false, now()
      FROM project p
      JOIN app_user c ON c.id = p.client_id
      WHERE c.assigned_consultant_id IS NOT NULL
        AND NOT EXISTS (
          SELECT 1
          FROM project_consultants existing
          WHERE existing.project_id = p.id
            AND existing.consultant_id = c.assigned_consultant_id
        )
    $copy$;
  END IF;
EXCEPTION WHEN others THEN
  RAISE NOTICE 'Skipping assigned_consultant_id migration to project_consultants: %', SQLERRM;
END $$;

ALTER TABLE app_user DROP CONSTRAINT IF EXISTS fk_app_user_assigned_consultant;
ALTER TABLE app_user DROP CONSTRAINT IF EXISTS fk_users_assigned_consultant;
DROP INDEX IF EXISTS idx_app_users_assigned_consultant;
ALTER TABLE app_user DROP COLUMN IF EXISTS assigned_consultant_id;

ALTER TABLE project
    ADD COLUMN IF NOT EXISTS client_id BIGINT,
    ADD COLUMN IF NOT EXISTS name VARCHAR(200),
    ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ DEFAULT now();

ALTER TABLE framework
    ADD COLUMN IF NOT EXISTS code VARCHAR(80),
    ADD COLUMN IF NOT EXISTS name VARCHAR(100),
    ADD COLUMN IF NOT EXISTS domain_scoring_method VARCHAR(40) NOT NULL DEFAULT 'DOMAIN_MINIMUM',
    ADD COLUMN IF NOT EXISTS score_scale VARCHAR(20) NOT NULL DEFAULT 'ZERO_TO_FIVE',
    ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ DEFAULT now();

ALTER TABLE project_framework
    ADD COLUMN IF NOT EXISTS project_id BIGINT,
    ADD COLUMN IF NOT EXISTS framework_id BIGINT,
    ADD COLUMN IF NOT EXISTS assigned_at TIMESTAMPTZ DEFAULT now();

ALTER TABLE project_consultants
    ADD COLUMN IF NOT EXISTS project_id BIGINT,
    ADD COLUMN IF NOT EXISTS consultant_id BIGINT,
    ADD COLUMN IF NOT EXISTS can_manage_project BOOLEAN DEFAULT FALSE,
    ADD COLUMN IF NOT EXISTS assigned_at TIMESTAMPTZ DEFAULT now();

DO $$
BEGIN
  IF to_regclass('project_consultant') IS NOT NULL THEN
    INSERT INTO project_consultants (project_id, consultant_id, can_manage_project, assigned_at)
    SELECT pc.project_id, pc.consultant_id, false, coalesce(pc.assigned_at, now())
    FROM project_consultant pc
    WHERE pc.project_id IS NOT NULL
      AND pc.consultant_id IS NOT NULL
      AND NOT EXISTS (
        SELECT 1
        FROM project_consultants existing
        WHERE existing.project_id = pc.project_id
          AND existing.consultant_id = pc.consultant_id
      );
  END IF;
EXCEPTION WHEN others THEN
  RAISE NOTICE 'Skipping project_consultant migration: %', SQLERRM;
END $$;

ALTER TABLE domain
    ADD COLUMN IF NOT EXISTS code VARCHAR(80),
    ADD COLUMN IF NOT EXISTS title VARCHAR(240),
    ADD COLUMN IF NOT EXISTS sort_order INTEGER DEFAULT 0,
    ADD COLUMN IF NOT EXISTS weight NUMERIC(10, 2),
    ADD COLUMN IF NOT EXISTS active BOOLEAN DEFAULT TRUE,
    ADD COLUMN IF NOT EXISTS framework_id BIGINT,
    ADD COLUMN IF NOT EXISTS parent_segment_id BIGINT;

ALTER TABLE sub_domain
    ADD COLUMN IF NOT EXISTS domain_id BIGINT,
    ADD COLUMN IF NOT EXISTS code VARCHAR(80),
    ADD COLUMN IF NOT EXISTS name VARCHAR(200),
    ADD COLUMN IF NOT EXISTS sort_order INTEGER DEFAULT 0,
    ADD COLUMN IF NOT EXISTS weight NUMERIC(10, 2),
    ADD COLUMN IF NOT EXISTS maturity_framework_id BIGINT,
    ADD COLUMN IF NOT EXISTS parent_segment_id BIGINT;

ALTER TABLE question
    ADD COLUMN IF NOT EXISTS domain_id BIGINT,
    ADD COLUMN IF NOT EXISTS code VARCHAR(120),
    ADD COLUMN IF NOT EXISTS text TEXT,
    ADD COLUMN IF NOT EXISTS sort_order INTEGER DEFAULT 0,
    ADD COLUMN IF NOT EXISTS active BOOLEAN DEFAULT TRUE,
    ADD COLUMN IF NOT EXISTS sub_domain_id BIGINT,
    ADD COLUMN IF NOT EXISTS weight NUMERIC(10, 2);

ALTER TABLE assessment
    ADD COLUMN IF NOT EXISTS client_id BIGINT,
    ADD COLUMN IF NOT EXISTS project_id BIGINT,
    ADD COLUMN IF NOT EXISTS year INTEGER,
    ADD COLUMN IF NOT EXISTS version INTEGER NOT NULL DEFAULT 1,
    ADD COLUMN IF NOT EXISTS status VARCHAR(20) NOT NULL DEFAULT 'DRAFT',
    ADD COLUMN IF NOT EXISTS is_submitted BOOLEAN NOT NULL DEFAULT FALSE,
    ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    ADD COLUMN IF NOT EXISTS submitted_at TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS version_comment VARCHAR(1000);

ALTER TABLE assessment_answer
    ADD COLUMN IF NOT EXISTS assessment_id BIGINT,
    ADD COLUMN IF NOT EXISTS question_id BIGINT,
    ADD COLUMN IF NOT EXISTS score INTEGER DEFAULT 0,
    ADD COLUMN IF NOT EXISTS note VARCHAR(1000),
    ADD COLUMN IF NOT EXISTS answered_at TIMESTAMPTZ DEFAULT now(),
    ADD COLUMN IF NOT EXISTS answered BOOLEAN NOT NULL DEFAULT FALSE,
    ADD COLUMN IF NOT EXISTS evidence_staff_rating VARCHAR(20),
    ADD COLUMN IF NOT EXISTS evidence_rated_by_id BIGINT,
    ADD COLUMN IF NOT EXISTS evidence_rated_at TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS evidence_staff_comment VARCHAR(1000),
    ADD COLUMN IF NOT EXISTS project_id BIGINT,
    ADD COLUMN IF NOT EXISTS is_submitted BOOLEAN DEFAULT FALSE,
    ADD COLUMN IF NOT EXISTS submitted_at TIMESTAMPTZ;

ALTER TABLE evidence
    ADD COLUMN IF NOT EXISTS uploaded_by_id BIGINT,
    ADD COLUMN IF NOT EXISTS storage_path TEXT,
    ADD COLUMN IF NOT EXISTS original_file_name VARCHAR(255),
    ADD COLUMN IF NOT EXISTS content_type VARCHAR(120) NOT NULL DEFAULT 'application/octet-stream',
    ADD COLUMN IF NOT EXISTS size_bytes BIGINT NOT NULL DEFAULT 0,
    ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ DEFAULT now(),
    ADD COLUMN IF NOT EXISTS answer_id BIGINT,
    ADD COLUMN IF NOT EXISTS staff_rating VARCHAR(20),
    ADD COLUMN IF NOT EXISTS rated_by_id BIGINT,
    ADD COLUMN IF NOT EXISTS rated_at TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS staff_comment VARCHAR(1000);

UPDATE app_user SET created_at = now() WHERE created_at IS NULL;
UPDATE project SET created_at = now() WHERE created_at IS NULL;
UPDATE framework SET created_at = now() WHERE created_at IS NULL;
UPDATE project_consultants SET can_manage_project = FALSE WHERE can_manage_project IS NULL;
UPDATE assessment SET created_at = now() WHERE created_at IS NULL;
UPDATE assessment_answer SET score = 0 WHERE score IS NULL;
UPDATE assessment_answer SET answered_at = now() WHERE answered_at IS NULL;
UPDATE assessment_answer aa
SET answered = FALSE
WHERE score = 0
  AND NOT EXISTS (
      SELECT 1 FROM evidence e WHERE e.answer_id = aa.id
  );
UPDATE assessment_answer SET answered = TRUE WHERE answered = FALSE AND score > 0;
UPDATE evidence SET created_at = now() WHERE created_at IS NULL;
UPDATE evidence SET content_type = 'application/octet-stream' WHERE content_type IS NULL OR content_type = '';
UPDATE evidence SET size_bytes = 0 WHERE size_bytes IS NULL;

UPDATE assessment_answer aa
SET evidence_staff_rating = src.staff_rating,
    evidence_rated_by_id = src.rated_by_id,
    evidence_rated_at = src.rated_at,
    evidence_staff_comment = src.staff_comment
FROM (
    SELECT DISTINCT ON (answer_id)
           answer_id,
           staff_rating,
           rated_by_id,
           rated_at,
           staff_comment
    FROM evidence
    WHERE answer_id IS NOT NULL
      AND staff_rating IS NOT NULL
    ORDER BY answer_id, rated_at DESC NULLS LAST, created_at DESC NULLS LAST, id DESC
) src
WHERE aa.id = src.answer_id
  AND aa.evidence_staff_rating IS NULL;

UPDATE framework
SET code = CASE
    WHEN lower(coalesce(name, '')) LIKE '%ndi%' THEN 'ndi'
    WHEN lower(coalesce(name, '')) LIKE '%cmmi%' THEN 'cmmi'
    ELSE 'framework_' || id
END
WHERE code IS NULL OR code = '';

INSERT INTO framework (code, name, domain_scoring_method, score_scale, created_at)
SELECT 'ndi', 'NDI', 'DOMAIN_MINIMUM', 'ZERO_TO_FIVE', now()
WHERE NOT EXISTS (
    SELECT 1 FROM framework WHERE lower(coalesce(code, name, '')) = 'ndi' OR lower(coalesce(name, '')) LIKE '%ndi%'
);

INSERT INTO framework (code, name, domain_scoring_method, score_scale, created_at)
SELECT 'cmmi', 'CMMI', 'DOMAIN_MINIMUM', 'ONE_TO_FIVE', now()
WHERE NOT EXISTS (
    SELECT 1 FROM framework WHERE lower(coalesce(code, name, '')) = 'cmmi' OR lower(coalesce(name, '')) LIKE '%cmmi%'
);

INSERT INTO domain (code, title, sort_order, weight, active, framework_id)
SELECT
    src.code,
    src.title,
    src.sort_order,
    src.weight,
    TRUE,
    (
        SELECT f.id
        FROM framework f
        WHERE lower(coalesce(f.code, f.name, '')) = 'ndi'
           OR lower(coalesce(f.name, '')) LIKE '%ndi%'
        ORDER BY f.id
        LIMIT 1
    )
FROM (
    VALUES
        ('ndi_dg',  'Data Governance (DG)',                         1,  11.75::NUMERIC),
        ('ndi_mcm', 'Data Catalog & Metadata Management (MCM)',      2,  10.88::NUMERIC),
        ('ndi_dq',  'Data Quality (DQ)',                             3,  11.93::NUMERIC),
        ('ndi_do',  'Data Operations (DO)',                          4,   4.39::NUMERIC),
        ('ndi_dcm', 'Document & Content Management (DCM)',           5,   3.16::NUMERIC),
        ('ndi_dam', 'Data Architecture & Modelling (DAM)',           6,   5.09::NUMERIC),
        ('ndi_dsi', 'Data Sharing & Interoperability (DSI)',         7,   8.95::NUMERIC),
        ('ndi_rmd', 'Reference & Master Data Management (RMD)',      8,   9.30::NUMERIC),
        ('ndi_bia', 'Business Intelligence & Analytics (BIA)',       9,   4.74::NUMERIC),
        ('ndi_dvr', 'Data Value Realization (DVR)',                 10,   3.68::NUMERIC),
        ('ndi_od',  'Open Data (OD)',                               11,   6.49::NUMERIC),
        ('ndi_foi', 'Freedom of Information (FOI)',                 12,   3.51::NUMERIC),
        ('ndi_dc',  'Data Classification (DC)',                     13,   6.84::NUMERIC),
        ('ndi_pdp', 'Personal Data Protection (PDP)',               14,   9.30::NUMERIC)
) AS src(code, title, sort_order, weight)
WHERE NOT EXISTS (
    SELECT 1
    FROM domain d
    WHERE lower(coalesce(d.code, '')) = src.code
);

UPDATE domain d
SET title = src.title,
    sort_order = src.sort_order,
    weight = src.weight,
    active = TRUE,
    framework_id = COALESCE(d.framework_id, (
        SELECT f.id
        FROM framework f
        WHERE lower(coalesce(f.code, f.name, '')) = 'ndi'
           OR lower(coalesce(f.name, '')) LIKE '%ndi%'
        ORDER BY f.id
        LIMIT 1
    ))
FROM (
    VALUES
        ('ndi_dg',  'Data Governance (DG)',                         1,  11.75::NUMERIC),
        ('ndi_mcm', 'Data Catalog & Metadata Management (MCM)',      2,  10.88::NUMERIC),
        ('ndi_dq',  'Data Quality (DQ)',                             3,  11.93::NUMERIC),
        ('ndi_do',  'Data Operations (DO)',                          4,   4.39::NUMERIC),
        ('ndi_dcm', 'Document & Content Management (DCM)',           5,   3.16::NUMERIC),
        ('ndi_dam', 'Data Architecture & Modelling (DAM)',           6,   5.09::NUMERIC),
        ('ndi_dsi', 'Data Sharing & Interoperability (DSI)',         7,   8.95::NUMERIC),
        ('ndi_rmd', 'Reference & Master Data Management (RMD)',      8,   9.30::NUMERIC),
        ('ndi_bia', 'Business Intelligence & Analytics (BIA)',       9,   4.74::NUMERIC),
        ('ndi_dvr', 'Data Value Realization (DVR)',                 10,   3.68::NUMERIC),
        ('ndi_od',  'Open Data (OD)',                               11,   6.49::NUMERIC),
        ('ndi_foi', 'Freedom of Information (FOI)',                 12,   3.51::NUMERIC),
        ('ndi_dc',  'Data Classification (DC)',                     13,   6.84::NUMERIC),
        ('ndi_pdp', 'Personal Data Protection (PDP)',               14,   9.30::NUMERIC)
) AS src(code, title, sort_order, weight)
WHERE lower(coalesce(d.code, '')) = src.code;

UPDATE question q
SET domain_id = d.id
FROM (
    SELECT lower(coalesce(code, '')) AS code, min(id) AS id
    FROM domain
    WHERE lower(coalesce(code, '')) LIKE 'ndi_%'
    GROUP BY lower(coalesce(code, ''))
) d
WHERE q.code IS NOT NULL
  AND d.code = regexp_replace(lower(q.code), '_[0-9]+$', '')
  AND lower(q.code) LIKE 'ndi_%'
  AND q.domain_id IS DISTINCT FROM d.id;

DO $$
DECLARE
  ndi_weight_sum NUMERIC;
BEGIN
  SELECT COALESCE(round(sum(weight), 2), 0)
  INTO ndi_weight_sum
  FROM domain
  WHERE lower(coalesce(code, '')) IN (
      'ndi_dg', 'ndi_mcm', 'ndi_dq', 'ndi_do', 'ndi_dcm', 'ndi_dam', 'ndi_dsi',
      'ndi_rmd', 'ndi_bia', 'ndi_dvr', 'ndi_od', 'ndi_foi', 'ndi_dc', 'ndi_pdp'
  );

  IF abs(ndi_weight_sum - 100.00) > 0.05 THEN
    RAISE NOTICE 'NDI domain weights sum is %, expected close to 100', ndi_weight_sum;
  END IF;
END $$;

UPDATE sub_domain sd
SET code = src.segment_code
FROM (
    SELECT
        q.sub_domain_id,
        regexp_replace(min(q.code), '_[0-9]+$', '') AS segment_code
    FROM question q
    WHERE q.sub_domain_id IS NOT NULL
      AND q.code IS NOT NULL
      AND q.code <> ''
    GROUP BY q.sub_domain_id
) src
WHERE sd.id = src.sub_domain_id
  AND (sd.code IS NULL OR sd.code = '');

UPDATE question q
SET domain_id = sd.domain_id
FROM sub_domain sd
WHERE q.sub_domain_id = sd.id
  AND q.domain_id IS NULL
  AND sd.domain_id IS NOT NULL;

DO $$
BEGIN
  IF EXISTS (
      SELECT 1
      FROM information_schema.columns
      WHERE table_schema = current_schema()
        AND table_name = 'sub_domain'
        AND column_name = 'weight'
  ) THEN
    UPDATE domain d
    SET weight = sd.weight
    FROM sub_domain sd
    WHERE d.id = sd.domain_id
      AND d.weight IS NULL
      AND sd.weight IS NOT NULL;

    UPDATE domain d
    SET weight = sd.weight
    FROM sub_domain sd
    WHERE lower(d.code) = lower(sd.code)
      AND d.weight IS NULL
      AND sd.weight IS NOT NULL;
  END IF;
END $$;

-- Reconnect old project-based answers to the newer versioned assessment table.
-- A legacy answer flag alone must not mark an assessment as submitted: only a real
-- submission timestamp is authoritative for the assessment lifecycle.
INSERT INTO assessment (client_id, project_id, year, version, status, is_submitted, created_at, submitted_at)
SELECT src.client_id, src.project_id, src.assessment_year, 1, src.status, src.status = 'SUBMITTED', src.created_at, src.submitted_at
FROM (
    SELECT
        p.client_id,
        max(p.id) AS project_id,
        EXTRACT(YEAR FROM COALESCE(p.created_at, now()))::INTEGER AS assessment_year,
        CASE
            WHEN max(aa.submitted_at) IS NOT NULL THEN 'SUBMITTED'
            ELSE 'DRAFT'
        END AS status,
        min(COALESCE(p.created_at, aa.answered_at, now())) AS created_at,
        max(aa.submitted_at) AS submitted_at
    FROM project p
    LEFT JOIN assessment_answer aa ON aa.project_id = p.id
    WHERE p.client_id IS NOT NULL
    GROUP BY p.client_id, EXTRACT(YEAR FROM COALESCE(p.created_at, now()))::INTEGER
) src
WHERE NOT EXISTS (
    SELECT 1
    FROM assessment a
    WHERE a.client_id = src.client_id
      AND a.year = src.assessment_year
      AND a.version = 1
);

UPDATE assessment_answer aa
SET assessment_id = a.id
FROM project p
JOIN assessment a
  ON a.client_id = p.client_id
 AND a.year = EXTRACT(YEAR FROM COALESCE(p.created_at, now()))::INTEGER
 AND a.version = 1
WHERE aa.project_id = p.id
  AND aa.assessment_id IS NULL;

-- Repair lifecycle columns after manual PostgreSQL structure changes.
UPDATE assessment a
SET project_id = src.project_id
FROM (
    SELECT assessment_id, max(project_id) AS project_id
    FROM assessment_answer
    WHERE assessment_id IS NOT NULL
      AND project_id IS NOT NULL
    GROUP BY assessment_id
) src
WHERE a.id = src.assessment_id
  AND a.project_id IS NULL;

UPDATE assessment a
SET project_id = p.id
FROM project p
WHERE a.project_id IS NULL
  AND p.client_id = a.client_id
  AND p.id = (
      SELECT p2.id
      FROM project p2
      WHERE p2.client_id = a.client_id
      ORDER BY p2.created_at DESC NULLS LAST, p2.id DESC
      LIMIT 1
  );

UPDATE assessment
SET status = upper(status)
WHERE status IS NOT NULL
  AND status <> upper(status);

UPDATE assessment
SET status = 'SUBMITTED'
WHERE submitted_at IS NOT NULL
  AND status <> 'SUBMITTED';

UPDATE assessment a
SET status = 'DRAFT',
    is_submitted = FALSE,
    submitted_at = NULL
WHERE status = 'SUBMITTED'
  AND EXISTS (
      SELECT 1
      FROM assessment_answer aa
      WHERE aa.assessment_id = a.id
        AND coalesce(aa.answered, FALSE) = FALSE
  );

UPDATE assessment
SET status = 'DRAFT',
    is_submitted = FALSE,
    submitted_at = NULL
WHERE status IS NULL
   OR status NOT IN ('DRAFT', 'SUBMITTED')
   OR (status = 'SUBMITTED' AND submitted_at IS NULL);

UPDATE assessment
SET submitted_at = NULL,
    is_submitted = FALSE
WHERE status = 'DRAFT'
  AND submitted_at IS NOT NULL;

UPDATE assessment
SET is_submitted = (status = 'SUBMITTED')
WHERE coalesce(is_submitted, FALSE) <> (status = 'SUBMITTED');

UPDATE assessment_answer
SET is_submitted = FALSE,
    submitted_at = NULL
WHERE coalesce(is_submitted, FALSE) = TRUE
   OR submitted_at IS NOT NULL;

ALTER TABLE assessment_answer
    DROP COLUMN IF EXISTS project_id,
    DROP COLUMN IF EXISTS is_submitted,
    DROP COLUMN IF EXISTS submitted_at;

-- Remove drafts that were created by opening a submitted assessment but never changed.
-- Evidence-bearing versions are intentionally kept because a copied file has a new storage path.
CREATE TEMP TABLE IF NOT EXISTS tmp_noop_draft_assessment_ids (
    id BIGINT PRIMARY KEY
);

TRUNCATE tmp_noop_draft_assessment_ids;

INSERT INTO tmp_noop_draft_assessment_ids (id)
SELECT a.id
FROM assessment a
JOIN assessment prev
  ON prev.client_id = a.client_id
 AND prev.year = a.year
 AND prev.version = a.version - 1
WHERE a.status = 'DRAFT'
  AND a.submitted_at IS NULL
  AND prev.status = 'SUBMITTED'
  AND NOT EXISTS (
      SELECT 1
      FROM assessment newer
      WHERE newer.client_id = a.client_id
        AND newer.year = a.year
        AND newer.version > a.version
  )
  AND NOT EXISTS (
      SELECT 1
      FROM evidence e
      JOIN assessment_answer aa ON aa.id = e.answer_id
      WHERE aa.assessment_id IN (a.id, prev.id)
  )
  AND NOT EXISTS (
      SELECT question_id, score, answered, note
      FROM assessment_answer
      WHERE assessment_id = a.id
      EXCEPT
      SELECT question_id, score, answered, note
      FROM assessment_answer
      WHERE assessment_id = prev.id
  )
  AND NOT EXISTS (
      SELECT question_id, score, answered, note
      FROM assessment_answer
      WHERE assessment_id = prev.id
      EXCEPT
      SELECT question_id, score, answered, note
      FROM assessment_answer
      WHERE assessment_id = a.id
  );

DELETE FROM assessment_answer aa
USING tmp_noop_draft_assessment_ids n
WHERE aa.assessment_id = n.id;

DELETE FROM assessment a
USING tmp_noop_draft_assessment_ids n
WHERE a.id = n.id;

DROP TABLE IF EXISTS tmp_noop_draft_assessment_ids;

DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'ck_assessment_status') THEN
    ALTER TABLE assessment
      ADD CONSTRAINT ck_assessment_status
      CHECK (status IN ('DRAFT', 'SUBMITTED'))
      NOT VALID;
  END IF;
EXCEPTION WHEN others THEN
  RAISE NOTICE 'Skipping ck_assessment_status: %', SQLERRM;
END $$;

DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'fk_app_user_managed_by') THEN
    ALTER TABLE app_user
      ADD CONSTRAINT fk_app_user_managed_by
      FOREIGN KEY (managed_by_id) REFERENCES app_user(id)
      ON DELETE SET NULL
      NOT VALID;
  END IF;
EXCEPTION WHEN others THEN
  RAISE NOTICE 'Skipping fk_app_user_managed_by: %', SQLERRM;
END $$;

DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'fk_project_client') THEN
    ALTER TABLE project
      ADD CONSTRAINT fk_project_client
      FOREIGN KEY (client_id) REFERENCES app_user(id)
      ON DELETE CASCADE
      NOT VALID;
  END IF;
EXCEPTION WHEN others THEN
  RAISE NOTICE 'Skipping fk_project_client: %', SQLERRM;
END $$;

DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'fk_project_framework_project') THEN
    ALTER TABLE project_framework
      ADD CONSTRAINT fk_project_framework_project
      FOREIGN KEY (project_id) REFERENCES project(id)
      ON DELETE CASCADE
      NOT VALID;
  END IF;
EXCEPTION WHEN others THEN
  RAISE NOTICE 'Skipping fk_project_framework_project: %', SQLERRM;
END $$;

DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'fk_project_framework_framework') THEN
    ALTER TABLE project_framework
      ADD CONSTRAINT fk_project_framework_framework
      FOREIGN KEY (framework_id) REFERENCES framework(id)
      ON DELETE CASCADE
      NOT VALID;
  END IF;
EXCEPTION WHEN others THEN
  RAISE NOTICE 'Skipping fk_project_framework_framework: %', SQLERRM;
END $$;

DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'fk_project_consultants_project') THEN
    IF EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'fk_project_consultant_project') THEN
      ALTER TABLE project_consultants
        RENAME CONSTRAINT fk_project_consultant_project TO fk_project_consultants_project;
    ELSE
      ALTER TABLE project_consultants
        ADD CONSTRAINT fk_project_consultants_project
        FOREIGN KEY (project_id) REFERENCES project(id)
        ON DELETE CASCADE
        NOT VALID;
    END IF;
  END IF;
EXCEPTION WHEN others THEN
  RAISE NOTICE 'Skipping fk_project_consultants_project: %', SQLERRM;
END $$;

DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'fk_project_consultants_consultant') THEN
    IF EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'fk_project_consultant_consultant') THEN
      ALTER TABLE project_consultants
        RENAME CONSTRAINT fk_project_consultant_consultant TO fk_project_consultants_consultant;
    ELSE
      ALTER TABLE project_consultants
        ADD CONSTRAINT fk_project_consultants_consultant
        FOREIGN KEY (consultant_id) REFERENCES app_user(id)
        ON DELETE CASCADE
        NOT VALID;
    END IF;
  END IF;
EXCEPTION WHEN others THEN
  RAISE NOTICE 'Skipping fk_project_consultants_consultant: %', SQLERRM;
END $$;

DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'fk_domain_framework') THEN
    ALTER TABLE domain
      ADD CONSTRAINT fk_domain_framework
      FOREIGN KEY (framework_id) REFERENCES framework(id)
      ON DELETE SET NULL
      NOT VALID;
  END IF;
EXCEPTION WHEN others THEN
  RAISE NOTICE 'Skipping fk_domain_framework: %', SQLERRM;
END $$;

DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'fk_sub_domain_domain') THEN
    ALTER TABLE sub_domain
      ADD CONSTRAINT fk_sub_domain_domain
      FOREIGN KEY (domain_id) REFERENCES domain(id)
      ON DELETE SET NULL
      NOT VALID;
  END IF;
EXCEPTION WHEN others THEN
  RAISE NOTICE 'Skipping fk_sub_domain_domain: %', SQLERRM;
END $$;

DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'fk_sub_domain_maturity_framework') THEN
    ALTER TABLE sub_domain
      ADD CONSTRAINT fk_sub_domain_maturity_framework
      FOREIGN KEY (maturity_framework_id) REFERENCES framework(id)
      ON DELETE SET NULL
      NOT VALID;
  END IF;
EXCEPTION WHEN others THEN
  RAISE NOTICE 'Skipping fk_sub_domain_maturity_framework: %', SQLERRM;
END $$;

DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'fk_sub_domain_parent_segment') THEN
    ALTER TABLE sub_domain
      ADD CONSTRAINT fk_sub_domain_parent_segment
      FOREIGN KEY (parent_segment_id) REFERENCES sub_domain(id)
      ON DELETE SET NULL
      NOT VALID;
  END IF;
EXCEPTION WHEN others THEN
  RAISE NOTICE 'Skipping fk_sub_domain_parent_segment: %', SQLERRM;
END $$;

DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'fk_question_sub_domain') THEN
    ALTER TABLE question
      ADD CONSTRAINT fk_question_sub_domain
      FOREIGN KEY (sub_domain_id) REFERENCES sub_domain(id)
      ON DELETE SET NULL
      NOT VALID;
  END IF;
EXCEPTION WHEN others THEN
  RAISE NOTICE 'Skipping fk_question_sub_domain: %', SQLERRM;
END $$;

DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'fk_question_domain') THEN
    ALTER TABLE question
      ADD CONSTRAINT fk_question_domain
      FOREIGN KEY (domain_id) REFERENCES domain(id)
      ON DELETE SET NULL
      NOT VALID;
  END IF;
EXCEPTION WHEN others THEN
  RAISE NOTICE 'Skipping fk_question_domain: %', SQLERRM;
END $$;

DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'fk_assessment_client') THEN
    ALTER TABLE assessment
      ADD CONSTRAINT fk_assessment_client
      FOREIGN KEY (client_id) REFERENCES app_user(id)
      ON DELETE CASCADE
      NOT VALID;
  END IF;
EXCEPTION WHEN others THEN
  RAISE NOTICE 'Skipping fk_assessment_client: %', SQLERRM;
END $$;

DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'fk_assessment_project') THEN
    ALTER TABLE assessment
      ADD CONSTRAINT fk_assessment_project
      FOREIGN KEY (project_id) REFERENCES project(id)
      ON DELETE SET NULL
      NOT VALID;
  END IF;
EXCEPTION WHEN others THEN
  RAISE NOTICE 'Skipping fk_assessment_project: %', SQLERRM;
END $$;

DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'ck_assessment_is_submitted_matches_status') THEN
    ALTER TABLE assessment
      ADD CONSTRAINT ck_assessment_is_submitted_matches_status
      CHECK (is_submitted = (status = 'SUBMITTED'))
      NOT VALID;
  END IF;
EXCEPTION WHEN others THEN
  RAISE NOTICE 'Skipping ck_assessment_is_submitted_matches_status: %', SQLERRM;
END $$;

DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'fk_assessment_answer_assessment') THEN
    ALTER TABLE assessment_answer
      ADD CONSTRAINT fk_assessment_answer_assessment
      FOREIGN KEY (assessment_id) REFERENCES assessment(id)
      ON DELETE CASCADE
      NOT VALID;
  END IF;
EXCEPTION WHEN others THEN
  RAISE NOTICE 'Skipping fk_assessment_answer_assessment: %', SQLERRM;
END $$;

DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'fk_assessment_answer_question') THEN
    ALTER TABLE assessment_answer
      ADD CONSTRAINT fk_assessment_answer_question
      FOREIGN KEY (question_id) REFERENCES question(id)
      ON DELETE CASCADE
      NOT VALID;
  END IF;
EXCEPTION WHEN others THEN
  RAISE NOTICE 'Skipping fk_assessment_answer_question: %', SQLERRM;
END $$;

DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'fk_evidence_answer') THEN
    ALTER TABLE evidence
      ADD CONSTRAINT fk_evidence_answer
      FOREIGN KEY (answer_id) REFERENCES assessment_answer(id)
      ON DELETE CASCADE
      NOT VALID;
  END IF;
EXCEPTION WHEN others THEN
  RAISE NOTICE 'Skipping fk_evidence_answer: %', SQLERRM;
END $$;

DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'fk_evidence_uploaded_by') THEN
    ALTER TABLE evidence
      ADD CONSTRAINT fk_evidence_uploaded_by
      FOREIGN KEY (uploaded_by_id) REFERENCES app_user(id)
      ON DELETE SET NULL
      NOT VALID;
  END IF;
EXCEPTION WHEN others THEN
  RAISE NOTICE 'Skipping fk_evidence_uploaded_by: %', SQLERRM;
END $$;

DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'fk_assessment_answer_evidence_rated_by') THEN
    ALTER TABLE assessment_answer
      ADD CONSTRAINT fk_assessment_answer_evidence_rated_by
      FOREIGN KEY (evidence_rated_by_id) REFERENCES app_user(id)
      ON DELETE SET NULL
      NOT VALID;
  END IF;
EXCEPTION WHEN others THEN
  RAISE NOTICE 'Skipping fk_assessment_answer_evidence_rated_by: %', SQLERRM;
END $$;

DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'fk_evidence_rated_by') THEN
    ALTER TABLE evidence
      ADD CONSTRAINT fk_evidence_rated_by
      FOREIGN KEY (rated_by_id) REFERENCES app_user(id)
      ON DELETE SET NULL
      NOT VALID;
  END IF;
EXCEPTION WHEN others THEN
  RAISE NOTICE 'Skipping fk_evidence_rated_by: %', SQLERRM;
END $$;

DO $$
BEGIN
  CREATE UNIQUE INDEX IF NOT EXISTS ux_app_user_email ON app_user (lower(email)) WHERE email IS NOT NULL;
EXCEPTION WHEN others THEN
  RAISE NOTICE 'Skipping ux_app_user_email: %', SQLERRM;
END $$;

DO $$
BEGIN
  CREATE UNIQUE INDEX IF NOT EXISTS ux_app_user_full_name ON app_user (lower(full_name)) WHERE full_name IS NOT NULL;
EXCEPTION WHEN others THEN
  RAISE NOTICE 'Skipping ux_app_user_full_name: %', SQLERRM;
END $$;

DO $$
BEGIN
  CREATE UNIQUE INDEX IF NOT EXISTS ux_framework_code ON framework (lower(code)) WHERE code IS NOT NULL;
EXCEPTION WHEN others THEN
  RAISE NOTICE 'Skipping ux_framework_code: %', SQLERRM;
END $$;

DO $$
BEGIN
  CREATE UNIQUE INDEX IF NOT EXISTS ux_sub_domain_code ON sub_domain (lower(code)) WHERE code IS NOT NULL;
EXCEPTION WHEN others THEN
  RAISE NOTICE 'Skipping ux_sub_domain_code: %', SQLERRM;
END $$;

DO $$
BEGIN
  CREATE UNIQUE INDEX IF NOT EXISTS ux_question_code ON question (lower(code)) WHERE code IS NOT NULL;
EXCEPTION WHEN others THEN
  RAISE NOTICE 'Skipping ux_question_code: %', SQLERRM;
END $$;

DO $$
BEGIN
  DELETE FROM project_consultants pc
  USING project_consultants duplicate
  WHERE pc.project_id = duplicate.project_id
    AND pc.consultant_id = duplicate.consultant_id
    AND pc.ctid < duplicate.ctid;
EXCEPTION WHEN others THEN
  RAISE NOTICE 'Skipping project_consultants duplicate cleanup: %', SQLERRM;
END $$;

DO $$
BEGIN
  DELETE FROM project_consultants pc
  WHERE pc.project_id IS NULL
     OR pc.consultant_id IS NULL
     OR NOT EXISTS (
         SELECT 1
         FROM project p
         WHERE p.id = pc.project_id
     )
     OR NOT EXISTS (
         SELECT 1
         FROM app_user u
         WHERE u.id = pc.consultant_id
     );
EXCEPTION WHEN others THEN
  RAISE NOTICE 'Skipping project_consultants invalid row cleanup: %', SQLERRM;
END $$;

DO $$
BEGIN
  ALTER TABLE project_consultants
    ALTER COLUMN project_id SET NOT NULL,
    ALTER COLUMN consultant_id SET NOT NULL,
    ALTER COLUMN can_manage_project SET NOT NULL;
EXCEPTION WHEN others THEN
  RAISE NOTICE 'Skipping project_consultants NOT NULL enforcement: %', SQLERRM;
END $$;

DO $$
DECLARE
  existing_pk_name text;
BEGIN
  SELECT conname
  INTO existing_pk_name
  FROM pg_constraint
  WHERE conrelid = 'project_consultants'::regclass
    AND contype = 'p'
  LIMIT 1;

  IF existing_pk_name IS NULL THEN
    ALTER TABLE project_consultants
      ADD CONSTRAINT pk_project_consultants PRIMARY KEY (project_id, consultant_id);
  ELSIF existing_pk_name <> 'pk_project_consultants'
      AND NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'pk_project_consultants') THEN
    EXECUTE format(
      'ALTER TABLE project_consultants RENAME CONSTRAINT %I TO pk_project_consultants',
      existing_pk_name
    );
  END IF;
EXCEPTION WHEN others THEN
  RAISE NOTICE 'Skipping pk_project_consultants: %', SQLERRM;
END $$;

DO $$
BEGIN
  CREATE UNIQUE INDEX IF NOT EXISTS ux_project_consultant_pair ON project_consultants (project_id, consultant_id);
EXCEPTION WHEN others THEN
  RAISE NOTICE 'Skipping ux_project_consultant_pair: %', SQLERRM;
END $$;

DO $$
BEGIN
  CREATE INDEX IF NOT EXISTS idx_project_consultants_project_id ON project_consultants (project_id);
EXCEPTION WHEN others THEN
  RAISE NOTICE 'Skipping idx_project_consultants_project_id: %', SQLERRM;
END $$;

DO $$
BEGIN
  CREATE INDEX IF NOT EXISTS idx_project_consultants_consultant_id ON project_consultants (consultant_id);
EXCEPTION WHEN others THEN
  RAISE NOTICE 'Skipping idx_project_consultants_consultant_id: %', SQLERRM;
END $$;

DO $$
BEGIN
  ALTER TABLE project_consultants VALIDATE CONSTRAINT fk_project_consultants_project;
EXCEPTION WHEN others THEN
  RAISE NOTICE 'Skipping fk_project_consultants_project validation: %', SQLERRM;
END $$;

DO $$
BEGIN
  ALTER TABLE project_consultants VALIDATE CONSTRAINT fk_project_consultants_consultant;
EXCEPTION WHEN others THEN
  RAISE NOTICE 'Skipping fk_project_consultants_consultant validation: %', SQLERRM;
END $$;

DO $$
BEGIN
  CREATE UNIQUE INDEX IF NOT EXISTS ux_assessment_client_year_version
    ON assessment (client_id, year, version)
    WHERE client_id IS NOT NULL AND year IS NOT NULL;
EXCEPTION WHEN others THEN
  RAISE NOTICE 'Skipping ux_assessment_client_year_version: %', SQLERRM;
END $$;

DO $$
BEGIN
  CREATE UNIQUE INDEX IF NOT EXISTS ux_assessment_answer_assessment_question
    ON assessment_answer (assessment_id, question_id)
    WHERE assessment_id IS NOT NULL AND question_id IS NOT NULL;
EXCEPTION WHEN others THEN
  RAISE NOTICE 'Skipping ux_assessment_answer_assessment_question: %', SQLERRM;
END $$;

DO $$
BEGIN
  ALTER TABLE evidence DROP CONSTRAINT IF EXISTS uq_evidence_answer;
  ALTER TABLE evidence DROP CONSTRAINT IF EXISTS evidence_answer_id_key;
  DROP INDEX IF EXISTS ux_evidence_answer;
  CREATE INDEX IF NOT EXISTS idx_evidence_answer ON evidence (answer_id) WHERE answer_id IS NOT NULL;
EXCEPTION WHEN others THEN
  RAISE NOTICE 'Skipping idx_evidence_answer: %', SQLERRM;
END $$;
