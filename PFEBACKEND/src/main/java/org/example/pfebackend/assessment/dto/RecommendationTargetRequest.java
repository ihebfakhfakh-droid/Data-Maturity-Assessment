package org.example.pfebackend.assessment.dto;

import jakarta.validation.constraints.DecimalMax;
import jakarta.validation.constraints.DecimalMin;
import jakarta.validation.constraints.NotNull;

public record RecommendationTargetRequest(
        @NotNull(message = "targetScore is required")
        @DecimalMin(value = "0.0", inclusive = false, message = "targetScore must be greater than 0")
        @DecimalMax(value = "5.0", message = "targetScore must not exceed 5")
        Double targetScore
) {
}
