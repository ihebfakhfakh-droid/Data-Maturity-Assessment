package org.example.pfebackend.evidence.dto;

import org.example.pfebackend.evidence.EvidenceRating;

import java.time.Instant;

public record EvidenceUploadResponse(
        Long evidenceId,
        Long assessmentId,
        String originalFileName,
        String contentType,
        long sizeBytes,
        EvidenceRating staffRating,
        Instant createdAt
) {
}

