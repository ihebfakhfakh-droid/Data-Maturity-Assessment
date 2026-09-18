-- Audit domain codes/titles stored in PostgreSQL.
-- This version follows the table requested by the user: domain(id, code, title, framework_id).

-- 1) List every stored domain with framework_id, code, and title.
SELECT
  id,
  code,
  title,
  framework_id
FROM domain
ORDER BY framework_id, code, id;

-- 2) Exact missing-title check requested.
SELECT
  id,
  code,
  title
FROM domain
WHERE title IS NULL
   OR BTRIM(title) = ''
ORDER BY code, id;

-- 3) Domains whose title exists but still looks like a technical code or abbreviation.
SELECT
  id,
  code,
  title,
  framework_id
FROM domain
WHERE
  title ~* '^(ndi|cmmi)[_ -]'
  OR title ~ '^[0-9]+([ ._-][0-9]+)+$'
  OR title ~ '^[A-Z]{2,5}$'
ORDER BY framework_id, code, id;

-- 4) Focus on the domains reported by the UI.
SELECT
  id,
  code,
  title,
  framework_id
FROM domain
WHERE code IN ('ndi_bia', 'ndi_dc', 'ndi_dcm', 'ndi_dvr', 'ndi_foi', 'ndi_od', 'ndi_pdp')
ORDER BY code, id;

-- 5) Safe corrections only for NDI domains confirmed in the current dataset/UI.
UPDATE domain SET title = 'Data Governance' WHERE code = 'ndi_dg' AND (title IS NULL OR BTRIM(title) = '' OR title = 'DG');
UPDATE domain SET title = 'Data Operations' WHERE code = 'ndi_do' AND (title IS NULL OR BTRIM(title) = '' OR title = 'DO');
UPDATE domain SET title = 'Metadata Management' WHERE code = 'ndi_mcm' AND (title IS NULL OR BTRIM(title) = '' OR title = 'MCM');
UPDATE domain SET title = 'Data Quality' WHERE code = 'ndi_dq' AND (title IS NULL OR BTRIM(title) = '' OR title = 'DQ');
UPDATE domain SET title = 'Data Architecture' WHERE code = 'ndi_da' AND (title IS NULL OR BTRIM(title) = '' OR title = 'DA');
UPDATE domain SET title = 'Data Architecture Management' WHERE code = 'ndi_dam' AND (title IS NULL OR BTRIM(title) = '' OR title = 'DAM');
UPDATE domain SET title = 'Data Classification' WHERE code = 'ndi_dc' AND (title IS NULL OR BTRIM(title) = '' OR title = 'DC');
UPDATE domain SET title = 'Data Change Management' WHERE code = 'ndi_dcm' AND (title IS NULL OR BTRIM(title) = '' OR title = 'DCM');
UPDATE domain SET title = 'Data Management' WHERE code = 'ndi_dm' AND (title IS NULL OR BTRIM(title) = '' OR title = 'DM');
UPDATE domain SET title = 'Data Sharing and Integration' WHERE code = 'ndi_dsi' AND (title IS NULL OR BTRIM(title) = '' OR title = 'DSI');
UPDATE domain SET title = 'Data Value Realization' WHERE code = 'ndi_dvr' AND (title IS NULL OR BTRIM(title) = '' OR title = 'DVR');
UPDATE domain SET title = 'Freedom of Information' WHERE code = 'ndi_foi' AND (title IS NULL OR BTRIM(title) = '' OR title = 'FOI');
UPDATE domain SET title = 'Business Intelligence and Analytics' WHERE code = 'ndi_bia' AND (title IS NULL OR BTRIM(title) = '' OR title = 'BIA');
UPDATE domain SET title = 'Open Data' WHERE code = 'ndi_od' AND (title IS NULL OR BTRIM(title) = '' OR title = 'OD');
UPDATE domain SET title = 'Personal Data Protection' WHERE code = 'ndi_pdp' AND (title IS NULL OR BTRIM(title) = '' OR title = 'PDP');
UPDATE domain SET title = 'Reference and Master Data' WHERE code = 'ndi_rmd' AND (title IS NULL OR BTRIM(title) = '' OR title = 'RMD');

-- 6) After applying corrections, re-run checks 1, 2, and 3.

-- 7) CMMI domains: list every CMMI domain stored in PostgreSQL.
SELECT
  d.id,
  d.code,
  d.title,
  d.framework_id
FROM domain d
WHERE d.framework_id IN (
  SELECT f.id
  FROM framework f
  WHERE f.name ILIKE '%CMMI%'
     OR f.code ILIKE '%CMMI%'
)
ORDER BY d.code, d.id;

-- 8) CMMI domains with missing titles.
SELECT
  d.id,
  d.code,
  d.title,
  d.framework_id
FROM domain d
WHERE d.framework_id IN (
  SELECT f.id
  FROM framework f
  WHERE f.name ILIKE '%CMMI%'
     OR f.code ILIKE '%CMMI%'
)
AND (
  d.title IS NULL
  OR BTRIM(d.title) = ''
);

-- 9) CMMI domains whose title still looks like a technical code or incomplete value.
SELECT
  d.id,
  d.code,
  d.title,
  d.framework_id
FROM domain d
WHERE d.framework_id IN (
  SELECT f.id
  FROM framework f
  WHERE f.name ILIKE '%CMMI%'
     OR f.code ILIKE '%CMMI%'
)
AND (
  d.title ~* '^cmmi[_ -]'
  OR d.title ~ '^[0-9]+([ ._-][0-9]+)+$'
  OR d.title ~ '^[A-Z]{2,5}$'
);

-- 10) CMMI sub-domains: verify parent domain link, name, and sort_order.
SELECT
  sd.id AS sub_domain_id,
  sd.domain_id,
  d.code AS domain_code,
  d.title AS domain_title,
  sd.name AS sub_domain_name,
  sd.sort_order
FROM sub_domain sd
JOIN domain d ON d.id = sd.domain_id
WHERE d.framework_id IN (
  SELECT f.id
  FROM framework f
  WHERE f.name ILIKE '%CMMI%'
     OR f.code ILIKE '%CMMI%'
)
ORDER BY d.code, sd.sort_order, sd.id;

-- 11) Sub-domains with missing names.
SELECT *
FROM sub_domain
WHERE name IS NULL
   OR BTRIM(name) = '';

-- 12) CMMI sub-domains whose name still looks like a technical code or incomplete value.
SELECT
  sd.id AS sub_domain_id,
  sd.domain_id,
  d.code AS domain_code,
  d.title AS domain_title,
  sd.name AS sub_domain_name,
  sd.sort_order
FROM sub_domain sd
JOIN domain d ON d.id = sd.domain_id
WHERE d.framework_id IN (
  SELECT f.id
  FROM framework f
  WHERE f.name ILIKE '%CMMI%'
     OR f.code ILIKE '%CMMI%'
)
AND (
  sd.name ~* '^cmmi[_ -]'
  OR sd.name ~ '^[0-9]+([ ._-][0-9]+)+$'
  OR sd.name ~ '^[A-Z]{2,5}$'
)
ORDER BY d.code, sd.sort_order, sd.id;

-- 13) Use the result of checks 8, 9, 11, and 12 to restore the real CMMI titles/names.
-- Do not update CMMI names blindly from frontend fallbacks. The correct source is backend seed/import data.

-- 14) Full CMMI hierarchy: Domain -> Sub-domain -> Question.
SELECT
  d.id AS domain_id,
  d.code AS domain_code,
  d.title AS domain_title,
  sd.id AS sub_domain_id,
  sd.name AS sub_domain_name,
  sd.sort_order AS sub_domain_sort_order,
  q.id AS question_id,
  q.code AS question_code,
  q.text AS question_text,
  q.sort_order AS question_sort_order
FROM domain d
LEFT JOIN sub_domain sd ON sd.domain_id = d.id
LEFT JOIN question q ON q.sub_domain_id = sd.id
WHERE d.framework_id IN (
  SELECT f.id
  FROM framework f
  WHERE f.name ILIKE '%CMMI%'
     OR f.code ILIKE '%CMMI%'
)
ORDER BY d.code, sd.sort_order, sd.id, q.sort_order, q.id;

-- 15) CMMI domains without sub-domains.
SELECT
  d.id,
  d.code,
  d.title,
  d.framework_id
FROM domain d
WHERE d.framework_id IN (
  SELECT f.id
  FROM framework f
  WHERE f.name ILIKE '%CMMI%'
     OR f.code ILIKE '%CMMI%'
)
AND NOT EXISTS (
  SELECT 1
  FROM sub_domain sd
  WHERE sd.domain_id = d.id
);

-- 16) CMMI sub-domains without questions.
SELECT
  sd.id AS sub_domain_id,
  sd.domain_id,
  d.code AS domain_code,
  d.title AS domain_title,
  sd.name AS sub_domain_name,
  sd.sort_order
FROM sub_domain sd
JOIN domain d ON d.id = sd.domain_id
WHERE d.framework_id IN (
  SELECT f.id
  FROM framework f
  WHERE f.name ILIKE '%CMMI%'
     OR f.code ILIKE '%CMMI%'
)
AND NOT EXISTS (
  SELECT 1
  FROM question q
  WHERE q.sub_domain_id = sd.id
);

-- 17) Questions with missing or broken CMMI links.
SELECT
  q.id AS question_id,
  q.code AS question_code,
  q.text AS question_text,
  q.domain_id,
  q.sub_domain_id,
  d.code AS domain_code,
  d.title AS domain_title,
  sd.name AS sub_domain_name
FROM question q
LEFT JOIN domain d ON d.id = q.domain_id
LEFT JOIN sub_domain sd ON sd.id = q.sub_domain_id
WHERE
  q.code ILIKE 'cmmi_%'
  AND (
    q.domain_id IS NULL
    OR q.sub_domain_id IS NULL
    OR d.id IS NULL
    OR sd.id IS NULL
    OR sd.domain_id <> q.domain_id
  )
ORDER BY q.code, q.id;

-- 18) Questions whose text is missing.
SELECT
  q.id,
  q.code,
  q.domain_id,
  q.sub_domain_id,
  q.text
FROM question q
WHERE q.code ILIKE 'cmmi_%'
  AND (q.text IS NULL OR BTRIM(q.text) = '')
ORDER BY q.code, q.id;
