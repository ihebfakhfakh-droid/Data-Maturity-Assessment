package org.example.pfebackend.assessment.dto;

import java.time.Instant;
import java.util.List;
import org.example.pfebackend.evidence.EvidenceRating;

public record AssessmentResponse(
        Long id,
        int year,
        int version,
        int versionNumber,
        String status,
        String globalStatus,
        Long clientId,
        String clientName,
        String clientEmail,
        Instant createdAt,
        Instant submittedAt,
        Long submittedById,
        String submittedBy,
        String submittedByEmail,
        String submittedByRole,
        String versionComment,
        Double recommendationTargetScore,
        double globalScore,
        double globalAverageScore,
        String globalMaturityLabel,
        int answeredQuestions,
        int totalQuestions,
        boolean complete,
        boolean canSubmit,
        int progressPercent,
        String workflowStatus,
        List<FrameworkStatusDto> frameworkStatus,
        List<SegmentScoreDto> segments
) {
    public record FrameworkStatusDto(
            String frameworkCode,
            String frameworkStatus,
            Double frameworkScore,
            Double frameworkAverageScore,
            int answeredQuestions,
            int totalQuestions,
            boolean isComplete,
            Instant lastSubmissionDate,
            Instant submittedAt
    ) {
    }

    public record SegmentScoreDto(
            String id,
            String segmentCode,
            String segmentTitle,
            double score,
            Double averageScore,
            String maturityLabel,
            int answeredQuestions,
            int totalQuestions,
            boolean complete,
            Double weight,
            List<QuestionAnswerDto> answers
    ) {
    }

    public record QuestionAnswerDto(
            Long questionId,
            String questionCode,
            String questionText,
            int score,
            String maturityLabel,
            String note,
            /** Dernière modification du score / de la ligne de réponse (historique). */
            Instant answeredAt,
            Long evidenceId,
            String evidenceUrl,
            String evidenceFileName,
            EvidenceRating evidenceStaffRating,
            String evidenceStaffComment,
            List<EvidenceDto> evidences,
            boolean answered
    ) {
    }

    public record EvidenceDto(
            Long id,
            String fileName,
            String fileUrl,
            String downloadUrl,
            Instant uploadedAt
    ) {
    }
}

