package org.example.pfebackend.assessment;

import java.util.Comparator;
import java.util.List;
import java.util.Locale;
import java.util.Map;

final class QuestionnaireOrdering {

    private static final Map<String, Integer> NDI_SEGMENT_ORDER = orderMap(List.of(
            "ndi_dg",
            "ndi_mcm",
            "ndi_dq",
            "ndi_do",
            "ndi_dcm",
            "ndi_dam",
            "ndi_dsi",
            "ndi_rmd",
            "ndi_bia",
            "ndi_dvr",
            "ndi_od",
            "ndi_foi",
            "ndi_dc",
            "ndi_pdp"
    ));

    private QuestionnaireOrdering() {
    }

    static Comparator<QuestionnaireQuestion> questionComparator() {
        return Comparator
                .comparingInt(QuestionnaireOrdering::segmentSortOrder)
                .thenComparingInt(QuestionnaireOrdering::questionSortOrder)
                .thenComparing(q -> safeLower(q.getCode()));
    }

    static int segmentSortOrder(QuestionnaireQuestion q) {
        String segmentCode = segmentCodeFor(q);
        String normalized = safeLower(segmentCode);
        if (normalized.startsWith("ndi_")) {
            return 10_000 + NDI_SEGMENT_ORDER.getOrDefault(normalized, 9_999);
        }
        if (normalized.startsWith("cmmi_")) {
            int parsed = parseCmmiSegmentOrder(normalized);
            if (parsed >= 0) {
                return 20_000 + parsed;
            }
        }
        QuestionnaireSegment segment = q.getSegment();
        if (segment != null && segment.getSortOrder() > 0) {
            return 30_000 + segment.getSortOrder();
        }
        return 40_000;
    }

    static int questionSortOrder(QuestionnaireQuestion q) {
        String code = safeLower(q.getCode());
        int lastUnderscore = code.lastIndexOf('_');
        if (lastUnderscore >= 0 && lastUnderscore + 1 < code.length()) {
            try {
                return Integer.parseInt(code.substring(lastUnderscore + 1));
            } catch (NumberFormatException ignored) {
                // Fall back to the legacy column below.
            }
        }
        return q.getSortOrder();
    }

    static String segmentCodeFor(QuestionnaireQuestion q) {
        String code = q.getCode();
        if (code == null || code.isBlank()) {
            return q.getSegment() != null ? "sub_domain_" + q.getSegment().getId() : "questions";
        }
        return code.replaceFirst("_[0-9]+$", "");
    }

    private static int parseCmmiSegmentOrder(String segmentCode) {
        String[] parts = segmentCode.split("_");
        if (parts.length < 3) {
            return -1;
        }
        try {
            int domain = Integer.parseInt(parts[1]);
            int subDomain = Integer.parseInt(parts[2]);
            return domain * 100 + subDomain;
        } catch (NumberFormatException ignored) {
            return -1;
        }
    }

    private static Map<String, Integer> orderMap(List<String> codes) {
        java.util.LinkedHashMap<String, Integer> order = new java.util.LinkedHashMap<>();
        for (int i = 0; i < codes.size(); i++) {
            order.put(codes.get(i), i + 1);
        }
        return order;
    }

    private static String safeLower(String value) {
        return value == null ? "" : value.toLowerCase(Locale.ROOT);
    }
}
