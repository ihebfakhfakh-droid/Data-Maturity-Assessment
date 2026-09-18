package org.example.pfebackend.assessment;

import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Service;

import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;

@Service
public class LegacyQuestionnaireMetadataService {

    private static final List<String> TITLE_COLUMNS = List.of(
            "name",
            "title",
            "label",
            "libelle",
            "libellé",
            "nom",
            "description",
            "sub_domain_name",
            "subdomain_name",
            "domain_name",
            "full_name"
    );

    private static final List<String> DOMAIN_ID_COLUMNS = List.of(
            "domain_id",
            "domainid",
            "parent_domain_id"
    );

    private static final Map<String, String> KNOWN_DOMAIN_LABELS = Map.ofEntries(
            Map.entry("DG", "Data Governance"),
            Map.entry("MCM", "Data Catalog & Metadata Management"),
            Map.entry("DQ", "Data Quality"),
            Map.entry("DO", "Data Operations"),
            Map.entry("DCM", "Document & Content Management"),
            Map.entry("DAM", "Data Architecture & Modelling"),
            Map.entry("DSI", "Data Sharing & Interoperability"),
            Map.entry("RMD", "Reference & Master Data Management"),
            Map.entry("BIA", "Business Intelligence & Analytics"),
            Map.entry("DVR", "Data Value Realization"),
            Map.entry("OD", "Open Data"),
            Map.entry("FOI", "Freedom of Information"),
            Map.entry("DC", "Data Classification"),
            Map.entry("PDP", "Personal Data Protection"),
            Map.entry("DWH", "Data Warehousing"),
            Map.entry("MDM", "Master Data Management"),
            Map.entry("DI", "Data Integration"),
            Map.entry("DS", "Data Security"),
            Map.entry("1 1", "1.1 Data Management Strategy"),
            Map.entry("1 2", "1.2 Communications"),
            Map.entry("1 3", "1.3 Data Management Function"),
            Map.entry("1 4", "1.4 Business Case"),
            Map.entry("1 5", "1.5 Program Funding"),
            Map.entry("2 1", "2.1 Governance Management"),
            Map.entry("2 2", "2.2 Business Glossary"),
            Map.entry("2 3", "2.3 Metadata Management"),
            Map.entry("3 1", "3.1 Data Quality Strategy"),
            Map.entry("3 2", "3.2 Data Profiling"),
            Map.entry("3 3", "3.3 Data Quality Assessment"),
            Map.entry("3 4", "3.4 Data Cleansing"),
            Map.entry("4 1", "4.1 Data Requirements Definition"),
            Map.entry("4 2", "4.2 Data Lifecycle Management"),
            Map.entry("4 3", "4.3 Provider Management"),
            Map.entry("5 1", "5.1 Architectural Approach"),
            Map.entry("5 2", "5.2 Architectural Standards"),
            Map.entry("5 3", "5.3 Data Management Platform"),
            Map.entry("5 4", "5.4 Data Integration"),
            Map.entry("5 5", "5.5 Historical Data, Archiving & Retention"),
            Map.entry("6 1", "6.1 Measurement and Analysis"),
            Map.entry("6 2", "6.2 Process Management"),
            Map.entry("6 3", "6.3 Process Quality Assurance"),
            Map.entry("6 4", "6.4 Risk Management"),
            Map.entry("6 5", "6.5 Configuration Management")
    );

    private final JdbcTemplate jdbcTemplate;
    private final Map<Long, String> subDomainTitleCache = new ConcurrentHashMap<>();
    private volatile String subDomainTitleColumn;
    private volatile boolean subDomainTitleColumnResolved;
    private volatile String subDomainDomainIdColumn;
    private volatile boolean subDomainDomainIdColumnResolved;
    private volatile String domainTitleColumn;
    private volatile boolean domainTitleColumnResolved;

    public LegacyQuestionnaireMetadataService(JdbcTemplate jdbcTemplate) {
        this.jdbcTemplate = jdbcTemplate;
    }

    public String titleFor(QuestionnaireQuestion question) {
        QuestionnaireDomain domain = question.getDomain();
        if (domain != null && hasText(domain.getTitle())) {
            return domain.getTitle();
        }
        QuestionnaireSegment segment = question.getSegment();
        if (segment == null || segment.getId() == null) {
            return fallbackTitle(question);
        }
        return subDomainTitleCache.computeIfAbsent(segment.getId(), id -> {
            String subDomainTitle = loadSubDomainTitle(id);
            String domainTitle = loadDomainTitle(id);
            if (hasText(domainTitle)) {
                if (!hasText(subDomainTitle) || isAbbreviation(subDomainTitle)) {
                    return domainTitle;
                }
                if (domainTitle.equalsIgnoreCase(subDomainTitle)) {
                    return domainTitle;
                }
                return domainTitle + " - " + subDomainTitle;
            }
            if (hasText(subDomainTitle)) {
                String known = knownLabel(subDomainTitle);
                return known != null ? known : subDomainTitle;
            }
            return fallbackTitle(question);
        });
    }

    private String loadSubDomainTitle(Long subDomainId) {
        String column = resolveSubDomainTitleColumn();
        if (column == null) {
            return null;
        }
        try {
            return jdbcTemplate.queryForObject(
                    "select " + column + "::text from sub_domain where id = ?",
                    String.class,
                    subDomainId
            );
        } catch (Exception ignored) {
            return null;
        }
    }

    private String loadDomainTitle(Long subDomainId) {
        String fkColumn = resolveSubDomainDomainIdColumn();
        String titleColumn = resolveDomainTitleColumn();
        if (fkColumn == null || titleColumn == null) {
            return null;
        }
        try {
            return jdbcTemplate.queryForObject(
                    "select d." + titleColumn + "::text from sub_domain sd join domain d on d.id = sd." + fkColumn + " where sd.id = ?",
                    String.class,
                    subDomainId
            );
        } catch (Exception ignored) {
            return null;
        }
    }

    private String resolveSubDomainTitleColumn() {
        if (subDomainTitleColumnResolved) {
            return subDomainTitleColumn;
        }
        for (String candidate : TITLE_COLUMNS) {
            if (columnExists("sub_domain", candidate)) {
                subDomainTitleColumn = candidate;
                subDomainTitleColumnResolved = true;
                return candidate;
            }
        }
        subDomainTitleColumnResolved = true;
        return null;
    }

    private String resolveSubDomainDomainIdColumn() {
        if (subDomainDomainIdColumnResolved) {
            return subDomainDomainIdColumn;
        }
        for (String candidate : DOMAIN_ID_COLUMNS) {
            if (columnExists("sub_domain", candidate)) {
                subDomainDomainIdColumn = candidate;
                subDomainDomainIdColumnResolved = true;
                return candidate;
            }
        }
        subDomainDomainIdColumnResolved = true;
        return null;
    }

    private String resolveDomainTitleColumn() {
        if (domainTitleColumnResolved) {
            return domainTitleColumn;
        }
        for (String candidate : TITLE_COLUMNS) {
            if (columnExists("domain", candidate)) {
                domainTitleColumn = candidate;
                domainTitleColumnResolved = true;
                return candidate;
            }
        }
        domainTitleColumnResolved = true;
        return null;
    }

    private boolean columnExists(String tableName, String columnName) {
        Integer count = jdbcTemplate.queryForObject(
                """
                        select count(*)
                        from information_schema.columns
                        where table_schema = current_schema()
                          and table_name = ?
                          and lower(column_name) = lower(?)
                        """,
                Integer.class,
                tableName,
                columnName
        );
        return count != null && count > 0;
    }

    private static String fallbackTitle(QuestionnaireQuestion question) {
        String code = question.getCode();
        if (code == null || code.isBlank()) {
            return "Questions";
        }
        String segment = code.replaceFirst("_[0-9]+$", "");
        String cleaned = segment
                .replaceFirst("^(ndi|cmmi)_", "")
                .replace('_', ' ')
                .trim();
        if (cleaned.isBlank()) {
            return "Questions";
        }
        String known = knownLabel(cleaned);
        if (known != null) {
            return known;
        }
        String[] words = cleaned.split("\\s+");
        StringBuilder title = new StringBuilder();
        for (String word : words) {
            if (word.isBlank()) {
                continue;
            }
            if (!title.isEmpty()) {
                title.append(' ');
            }
            title.append(word.substring(0, 1).toUpperCase(Locale.ROOT));
            if (word.length() > 1) {
                title.append(word.substring(1).toLowerCase(Locale.ROOT));
            }
        }
        return title.isEmpty() ? "Questions" : title.toString();
    }

    private static boolean hasText(String value) {
        return value != null && !value.isBlank();
    }

    private static boolean isAbbreviation(String value) {
        String normalized = value == null ? "" : value.trim();
        return !normalized.isBlank()
                && normalized.length() <= 8
                && normalized.equals(normalized.toUpperCase(Locale.ROOT))
                && !normalized.contains(" ");
    }

    private static String knownLabel(String raw) {
        if (raw == null) {
            return null;
        }
        String normalized = raw.trim()
                .replace('.', ' ')
                .replace('_', ' ')
                .replaceAll("\\s+", " ")
                .toUpperCase(Locale.ROOT);
        return KNOWN_DOMAIN_LABELS.get(normalized);
    }
}
