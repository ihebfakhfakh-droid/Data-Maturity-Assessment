package org.example.pfebackend.assessment;

import org.example.pfebackend.evidence.Evidence;
import org.example.pfebackend.evidence.EvidenceService;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.Instant;
import java.util.List;
import java.util.Set;

@Service
public class AssessmentVersioningService {

    private final AssessmentAnswerRepository answerRepository;
    private final EvidenceService evidenceService;

    public AssessmentVersioningService(
            AssessmentAnswerRepository answerRepository,
            EvidenceService evidenceService
    ) {
        this.answerRepository = answerRepository;
        this.evidenceService = evidenceService;
    }

    /**
     * Copies all answers and evidence files from {@code source} into {@code target} (new draft row).
     */
    @Transactional
    public void copyAnswersAndEvidence(Assessment source, Assessment target) {
        if (source.getId() != null && source.getId().equals(target.getId())) {
            return;
        }
        List<AssessmentAnswer> sourceAnswers = answerRepository.findByAssessment_Id(source.getId());
        for (AssessmentAnswer src : sourceAnswers) {
            AssessmentAnswer na = answerRepository
                    .findByAssessment_IdAndQuestion_Id(target.getId(), src.getQuestion().getId())
                    .orElseGet(() -> {
                        AssessmentAnswer created = new AssessmentAnswer();
                        created.setAssessment(target);
                        created.setQuestion(src.getQuestion());
                        return created;
                    });
            na.setScore(src.getScore());
            na.setAnswered(src.isAnswered());
            na.setNote(src.getNote());
            na.setAnsweredAt(src.getAnsweredAt() != null ? src.getAnsweredAt() : Instant.now());
            copyEvidenceRating(src, na);
            na = answerRepository.save(na);

            for (Evidence ev : src.getEvidences()) {
                evidenceService.copyEvidenceFork(ev, na);
            }
        }
    }

    /**
     * Carries forward already-submitted framework answers into a newer draft without
     * overwriting answers the client is currently editing.
     */
    @Transactional
    public void copyMissingAnswersAndEvidence(Assessment source, Assessment target, Set<String> frameworkTagsToCopy) {
        if (source.getId() != null && source.getId().equals(target.getId())) {
            return;
        }
        if (frameworkTagsToCopy == null || frameworkTagsToCopy.isEmpty()) {
            return;
        }
        List<AssessmentAnswer> sourceAnswers = answerRepository.findByAssessment_Id(source.getId());
        for (AssessmentAnswer src : sourceAnswers) {
            String frameworkTag = frameworkTagForQuestionCode(src.getQuestion().getCode());
            if (!frameworkTagsToCopy.contains(frameworkTag)) {
                continue;
            }
            if (answerRepository.findByAssessment_IdAndQuestion_Id(target.getId(), src.getQuestion().getId()).isPresent()) {
                continue;
            }

            AssessmentAnswer copied = new AssessmentAnswer();
            copied.setAssessment(target);
            copied.setQuestion(src.getQuestion());
            copied.setScore(src.getScore());
            copied.setAnswered(src.isAnswered());
            copied.setNote(src.getNote());
            copied.setAnsweredAt(src.getAnsweredAt() != null ? src.getAnsweredAt() : Instant.now());
            copyEvidenceRating(src, copied);
            copied = answerRepository.save(copied);

            for (Evidence ev : src.getEvidences()) {
                evidenceService.copyEvidenceFork(ev, copied);
            }
        }
    }

    private static void copyEvidenceRating(AssessmentAnswer src, AssessmentAnswer target) {
        target.setEvidenceStaffRating(src.getEvidenceStaffRating());
        target.setEvidenceStaffComment(src.getEvidenceStaffComment());
        target.setEvidenceRatedBy(src.getEvidenceRatedBy());
        target.setEvidenceRatedAt(src.getEvidenceRatedAt());
    }

    private static String frameworkTagForQuestionCode(String code) {
        if (code == null) {
            return null;
        }
        String normalized = code.toLowerCase(java.util.Locale.ROOT);
        if (normalized.startsWith("ndi_")) {
            return "NDI";
        }
        if (normalized.startsWith("cmmi_")) {
            return "CMMI";
        }
        return null;
    }
}
