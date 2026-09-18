package org.example.pfebackend.assessment.dto;

import jakarta.validation.constraints.Max;
import jakarta.validation.constraints.Min;

public record CreateAssessmentRequest(
        @Min(2000) @Max(2100) int year
) {
}

