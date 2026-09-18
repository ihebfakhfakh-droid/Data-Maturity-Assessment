package org.example.pfebackend.assessment.dto;

import jakarta.validation.Valid;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotEmpty;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Pattern;
import jakarta.validation.constraints.Size;
import org.example.pfebackend.assessment.DomainScoringMethod;
import org.example.pfebackend.assessment.FrameworkScoreScale;

import java.util.List;

public record CreateMaturityFrameworkRequest(
        @NotBlank
        @Pattern(regexp = "[a-z0-9][a-z0-9_]{0,79}", message = "code: 1-80 chars, lowercase letters, digits, underscore")
        @Size(max = 80)
        String code,
        @NotBlank @Size(max = 200) String name,
        @NotNull DomainScoringMethod domainScoringMethod,
        @NotNull FrameworkScoreScale scoreScale,
        @NotEmpty @Valid List<CreateFrameworkDomainRequest> domains
) {}
