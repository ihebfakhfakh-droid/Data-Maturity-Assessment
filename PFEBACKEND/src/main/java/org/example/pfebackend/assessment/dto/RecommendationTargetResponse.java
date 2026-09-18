package org.example.pfebackend.assessment.dto;

public record RecommendationTargetResponse(
        Long assessmentId,
        int version,
        String status,
        double currentGlobalScore,
        Double recommendationTargetScore,
        double maxScore
) {
}
