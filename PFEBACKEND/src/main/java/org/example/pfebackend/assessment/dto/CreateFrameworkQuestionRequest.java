package org.example.pfebackend.assessment.dto;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Size;

public record CreateFrameworkQuestionRequest(
        @NotBlank @Size(max = 120) String code,
        @NotBlank @Size(max = 500) String text,
        int sortOrder
) {}
