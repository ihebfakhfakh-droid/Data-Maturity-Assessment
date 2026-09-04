package org.example.pfebackend.assessment.dto;

import org.example.pfebackend.evidence.EvidenceRating;

import java.util.List;

public record AssessmentVersionDiffDto(
        Integer fromVersion,
        int toVersion,
        GlobalScoreDiff globalScore,
        List<SegmentScoreDiff> segmentScores,
        List<AnswerDiff> answers,
        List<EvidenceDiff> evidences
) {
    public record GlobalScoreDiff(Double oldScore, Double newScore, String oldLabel, String newLabel) {
    }

    public record SegmentScoreDiff(
            String segmentCode,
            String segmentTitle,
            String parentSegmentCode,
            String parentSegmentTitle,
            Double oldScore,
            Double newScore,
            String oldMaturityLabel,
            String newMaturityLabel
    ) {
    }

    public record AnswerDiff(
            String questionCode,
            String questionText,
            String segmentCode,
            String segmentTitle,
            String parentSegmentCode,
            String parentSegmentTitle,
            Integer oldScore,
            Integer newScore,
            String oldMaturityLabel,
            String newMaturityLabel
    ) {
    }

    public record EvidenceDiff(
            String questionCode,
            String changeType,
            String oldFileName,
            String newFileName,
            Long oldEvidenceId,
            Long newEvidenceId,
            EvidenceRating oldStaffRating,
            EvidenceRating newStaffRating,
            Long oldSizeBytes,
            Long newSizeBytes
    ) {
    }
}
