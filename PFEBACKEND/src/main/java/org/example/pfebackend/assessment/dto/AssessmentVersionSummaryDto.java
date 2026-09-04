package org.example.pfebackend.assessment.dto;

import java.time.Instant;
import java.util.List;

public record AssessmentVersionSummaryDto(
        Long assessmentId,
        int year,
        int version,
        int versionNumber,
        String status,
        String globalStatus,
        Instant createdAt,
        Instant submittedAt,
        String versionComment,
        double globalScore,
        double globalAverageScore,
        String globalMaturityLabel,
        List<String> frameworkTags,
        List<AssessmentResponse.FrameworkStatusDto> frameworkStatus,
        List<AssessmentResponse.FrameworkStatusDto> frameworkDetails,
        int answeredQuestions,
        int totalQuestions,
        boolean complete,
        int progressPercent,
        String workflowStatus
) {
}
