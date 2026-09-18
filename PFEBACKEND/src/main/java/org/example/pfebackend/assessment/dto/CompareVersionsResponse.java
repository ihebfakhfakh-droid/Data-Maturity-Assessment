package org.example.pfebackend.assessment.dto;

import org.example.pfebackend.evidence.EvidenceRating;

import java.util.List;

/**
 * Réponse structurée pour l’UI « Compare Versions » (deux snapshots d’évaluation).
 */
public record CompareVersionsResponse(
        int fromVersion,
        int toVersion,
        long fromAssessmentId,
        long toAssessmentId,
        ChangedScores changedScores,
        List<AnswerChange> changedAnswers,
        List<EvidenceChange> changedEvidences,
        List<ChangeItem> addedItems,
        List<ChangeItem> removedItems,
        List<ChangeItem> modifiedItems
) {

    public record ChangedScores(
            Double oldGlobalScore,
            Double newGlobalScore,
            String oldGlobalLabel,
            String newGlobalLabel,
            List<SegmentScoreChange> segments
    ) {
    }

    public record SegmentScoreChange(
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

    public record AnswerChange(
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

    public record EvidenceChange(
            String questionCode,
            String changeType,
            String oldFileName,
            String newFileName,
            Long oldEvidenceId,
            Long newEvidenceId,
            EvidenceRating oldStaffRating,
            EvidenceRating newStaffRating
    ) {
    }

    /**
     * @param category ANSWER | EVIDENCE | SEGMENT | GLOBAL
     */
    public record ChangeItem(
            String category,
            String code,
            String title,
            String detail
    ) {
    }
}
