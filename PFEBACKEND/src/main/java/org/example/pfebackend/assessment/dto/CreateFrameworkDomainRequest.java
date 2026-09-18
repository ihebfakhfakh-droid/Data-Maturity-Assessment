package org.example.pfebackend.assessment.dto;

import jakarta.validation.Valid;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Size;

import java.util.List;

public record CreateFrameworkDomainRequest(
        @NotBlank @Size(max = 80) String code,
        @NotBlank @Size(max = 200) String title,
        int sortOrder,
        Double weight,
        @Valid List<CreateFrameworkDomainRequest> subDomains,
        @Valid List<CreateFrameworkQuestionRequest> questions
) {}
