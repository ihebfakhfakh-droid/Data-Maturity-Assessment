package org.example.pfebackend.assessment.dto;

import java.util.List;

public record QuestionnaireResponse(
        List<SegmentDto> segments
) {
    public record SegmentDto(
            String code,
            String title,
            int sortOrder,
            /** {@code null} for built-in NDI/CMMI segments without a parent. */
            String parentSegmentCode,
            /** {@code null} unless this segment belongs to an admin-defined framework. */
            String maturityFrameworkCode,
            /** Domain-level weight percentage when configured, mainly for NDI domains. */
            Double weight,
            List<QuestionDto> questions
    ) {
    }

    public record QuestionDto(
            String code,
            String text,
            int sortOrder
    ) {
    }
}

