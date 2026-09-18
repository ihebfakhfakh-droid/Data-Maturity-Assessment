package org.example.pfebackend.evidence.dto;

import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Size;
import org.example.pfebackend.evidence.EvidenceRating;

public record RateEvidenceRequest(
        @NotNull EvidenceRating rating,
        @Size(max = 1000) String comment
) {
}

