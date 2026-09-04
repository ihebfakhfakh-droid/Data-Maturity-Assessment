package org.example.pfebackend.assessment;

import org.example.pfebackend.assessment.dto.AssessmentResponse;
import org.example.pfebackend.assessment.dto.GenerateReportRequestDto;
import org.example.pfebackend.assessment.dto.RecommendationTargetRequest;
import org.example.pfebackend.assessment.dto.RecommendationTargetResponse;
import org.example.pfebackend.project.Project;
import org.example.pfebackend.staff.StaffService;
import org.example.pfebackend.user.AppUser;
import org.example.pfebackend.user.Role;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.web.server.ResponseStatusException;

import java.time.ZoneId;
import java.time.format.DateTimeFormatter;
import java.util.LinkedHashMap;
import java.util.Locale;
import java.util.Map;
import java.util.Objects;

@Service
public class RecommendationService {

    private static final Logger log = LoggerFactory.getLogger(RecommendationService.class);

    public static final double MAX_FRAMEWORK_SCORE = 5.0;
    private static final String SUPPORTED_FRAMEWORK = "NDI";
    private static final DateTimeFormatter SUBMITTED_AT_FORMAT =
            DateTimeFormatter.ofPattern("dd/MM/yyyy HH:mm").withZone(ZoneId.systemDefault());

    private final AssessmentRepository assessmentRepository;
    private final AssessmentService assessmentService;
    private final StaffService staffService;
    private final AiRecommendationClient aiRecommendationClient;
    private final String datasourceUrl;

    public RecommendationService(
            AssessmentRepository assessmentRepository,
            AssessmentService assessmentService,
            StaffService staffService,
            AiRecommendationClient aiRecommendationClient,
            @Value("${spring.datasource.url:}") String datasourceUrl
    ) {
        this.assessmentRepository = assessmentRepository;
        this.assessmentService = assessmentService;
        this.staffService = staffService;
        this.aiRecommendationClient = aiRecommendationClient;
        this.datasourceUrl = datasourceUrl;
    }

    @Transactional
    public RecommendationTargetResponse setRecommendationTarget(
            AppUser staff,
            Long assessmentId,
            RecommendationTargetRequest request
    ) {
        Assessment requested = requireRecommendationActor(staff, assessmentId);
        logRecommendationContext("recommendation-target/request", requested);
        // Align with generateRecommendationReport: UI may open the current DRAFT row whose
        // globalStatus is SUBMITTED after a previous version was submitted.
        Assessment assessment = resolveLatestSubmitted(requested);
        logRecommendationContext("recommendation-target/resolved", assessment);
        assertSubmitted(assessment);
        assertNdiSupported(assessment);

        AssessmentResponse rendered = assessmentService.renderAssessment(assessment);
        double currentScore = resolveNdiGlobalScore(rendered);
        double targetScore = requireValidTarget(request.targetScore(), currentScore);

        assessment.setRecommendationTargetScore(targetScore);
        assessmentRepository.save(assessment);

        return new RecommendationTargetResponse(
                assessment.getId(),
                assessment.getVersion(),
                assessment.getStatus().name(),
                currentScore,
                assessment.getRecommendationTargetScore(),
                MAX_FRAMEWORK_SCORE
        );
    }

    @Transactional(readOnly = true)
    public RecommendationReportResult generateRecommendationReport(AppUser staff, Long assessmentId) {
        Assessment requested = requireRecommendationActor(staff, assessmentId);
        logRecommendationContext("recommendation-report/request", requested);
        Assessment assessment = resolveLatestSubmitted(requested);
        logRecommendationContext("recommendation-report/resolved", assessment);
        assertSubmitted(assessment);
        assertNdiSupported(assessment);

        if (assessment.getRecommendationTargetScore() == null) {
            throw new ResponseStatusException(
                    HttpStatus.BAD_REQUEST,
                    "Aucune cible de score n'a été définie pour cette évaluation soumise."
            );
        }

        AssessmentResponse rendered = assessmentService.renderAssessment(assessment);
        double currentScore = resolveNdiGlobalScore(rendered);
        double targetScore = requireValidTarget(assessment.getRecommendationTargetScore(), currentScore);

        Map<String, Integer> currentScores = buildNdiCurrentScores(rendered);
        if (currentScores.isEmpty()) {
            throw new ResponseStatusException(
                    HttpStatus.BAD_REQUEST,
                    "Aucune réponse NDI exploitable n'a été trouvée pour générer les recommandations."
            );
        }

        Map<String, Double> domainWeights = new LinkedHashMap<>();
        Map<String, Integer> domainScores = new LinkedHashMap<>();
        Map<String, Double> weightedScores = new LinkedHashMap<>();
        double totalWeights = buildNdiDomainMaps(rendered, domainWeights, domainScores, weightedScores);

        Project project = assessment.getProject();
        String projectName = project != null && project.getName() != null && !project.getName().isBlank()
                ? project.getName()
                : "projet";
        String clientName = assessment.getClient() != null
                ? Objects.requireNonNullElse(assessment.getClient().getFullName(), assessment.getClient().getEmail())
                : "client";

        String generationDate = java.time.LocalDateTime.now()
                .format(java.time.format.DateTimeFormatter.ofPattern("dd/MM/yyyy HH:mm"));

        GenerateReportRequestDto requestDto = new GenerateReportRequestDto(
                currentScore,
                targetScore,
                round3(totalWeights),
                domainWeights,
                domainScores,
                weightedScores,
                currentScores,
                SUPPORTED_FRAMEWORK,
                projectName,
                clientName,
                assessment.getVersion(),
                assessment.getSubmittedAt() != null ? SUBMITTED_AT_FORMAT.format(assessment.getSubmittedAt()) : null,
                generationDate
        );

        byte[] pdf = aiRecommendationClient.generateReportPdf(requestDto);
        String filename = buildReportFilename(projectName, assessment.getVersion());
        return new RecommendationReportResult(pdf, filename);
    }

    private Assessment requireRecommendationActor(AppUser staff, Long assessmentId) {
        if (staff.getRole() != Role.CONSULTANT && staff.getRole() != Role.MANAGER) {
            throw new ResponseStatusException(
                    HttpStatus.FORBIDDEN,
                    "Seuls les consultants et managers peuvent utiliser les recommandations IA."
            );
        }
        Assessment assessment = assessmentRepository.findById(assessmentId)
                .orElseThrow(() -> new ResponseStatusException(HttpStatus.NOT_FOUND, "Évaluation introuvable."));
        staffService.assertCanAccessAssessment(staff, assessment);
        return assessment;
    }

    private Assessment resolveLatestSubmitted(Assessment assessment) {
        if (assessment.getProject() != null && assessment.getProject().getId() != null) {
            return assessmentRepository
                    .findFirstByProject_IdAndStatusOrderByYearDescVersionDesc(
                            assessment.getProject().getId(),
                            AssessmentStatus.SUBMITTED
                    )
                    .orElseThrow(() -> new ResponseStatusException(
                            HttpStatus.BAD_REQUEST,
                            "Aucune évaluation soumise n'est disponible pour ce projet."
                    ));
        }
        return assessmentRepository
                .findFirstByClient_IdAndStatusOrderByYearDescVersionDesc(
                        assessment.getClient().getId(),
                        AssessmentStatus.SUBMITTED
                )
                .orElseThrow(() -> new ResponseStatusException(
                        HttpStatus.BAD_REQUEST,
                        "Aucune évaluation soumise n'est disponible pour ce client."
                ));
    }

    private static void assertSubmitted(Assessment assessment) {
        if (assessment.getStatus() != AssessmentStatus.SUBMITTED) {
            throw new ResponseStatusException(
                    HttpStatus.BAD_REQUEST,
                    "Les recommandations IA sont disponibles uniquement pour une évaluation soumise (SUBMITTED)."
            );
        }
    }

    private void logRecommendationContext(String phase, Assessment assessment) {
        Long projectId = assessment.getProject() != null ? assessment.getProject().getId() : null;
        log.info(
                "AI {} | assessmentId={} projectId={} version={} status={} isSubmitted={} datasourceUrl={} springProfiles={}",
                phase,
                assessment.getId(),
                projectId,
                assessment.getVersion(),
                assessment.getStatus(),
                assessment.isSubmitted(),
                datasourceUrl,
                System.getProperty("spring.profiles.active", "")
        );
    }

    private void assertNdiSupported(Assessment assessment) {
        AssessmentResponse rendered = assessmentService.renderAssessment(assessment);
        boolean hasNdi = rendered.frameworkStatus() != null && rendered.frameworkStatus().stream()
                .anyMatch(fw -> SUPPORTED_FRAMEWORK.equalsIgnoreCase(fw.frameworkCode()));
        boolean hasNdiAnswers = rendered.segments() != null && rendered.segments().stream()
                .anyMatch(segment -> segment.segmentCode() != null
                        && segment.segmentCode().toLowerCase(Locale.ROOT).startsWith("ndi_"));
        if (!hasNdi && !hasNdiAnswers) {
            throw new ResponseStatusException(
                    HttpStatus.BAD_REQUEST,
                    "La génération des recommandations IA n'est pas encore disponible pour ce framework."
            );
        }
    }

    private static double resolveNdiGlobalScore(AssessmentResponse rendered) {
        if (rendered.frameworkStatus() != null) {
            for (AssessmentResponse.FrameworkStatusDto fw : rendered.frameworkStatus()) {
                if (SUPPORTED_FRAMEWORK.equalsIgnoreCase(fw.frameworkCode()) && fw.frameworkScore() != null) {
                    return fw.frameworkScore();
                }
            }
        }
        return rendered.globalScore();
    }

    private static double requireValidTarget(Double targetScore, double currentScore) {
        if (targetScore == null || Double.isNaN(targetScore) || Double.isInfinite(targetScore)) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "La cible doit être un nombre valide.");
        }
        if (targetScore <= currentScore) {
            throw new ResponseStatusException(
                    HttpStatus.BAD_REQUEST,
                    "La cible doit être strictement supérieure au score global actuel (" + currentScore + ")."
            );
        }
        if (targetScore > MAX_FRAMEWORK_SCORE) {
            throw new ResponseStatusException(
                    HttpStatus.BAD_REQUEST,
                    "La cible ne doit pas dépasser le score maximal du framework (" + MAX_FRAMEWORK_SCORE + ")."
            );
        }
        if (targetScore <= 0) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "La cible doit être un nombre positif.");
        }
        return targetScore;
    }

    private static Map<String, Integer> buildNdiCurrentScores(AssessmentResponse rendered) {
        Map<String, Integer> scores = new LinkedHashMap<>();
        if (rendered.segments() == null) {
            return scores;
        }
        for (AssessmentResponse.SegmentScoreDto segment : rendered.segments()) {
            if (segment.segmentCode() == null
                    || !segment.segmentCode().toLowerCase(Locale.ROOT).startsWith("ndi_")) {
                continue;
            }
            if (segment.answers() == null) {
                continue;
            }
            for (AssessmentResponse.QuestionAnswerDto answer : segment.answers()) {
                if (!answer.answered() || answer.questionCode() == null || answer.questionCode().isBlank()) {
                    continue;
                }
                scores.put(answer.questionCode(), answer.score());
            }
        }
        return scores;
    }

    /**
     * Builds NDI domain maps using knowledge-base domain IDs (DG, DQ, …).
     *
     * @return totalWeights of domains that have at least one answered question
     */
    private static double buildNdiDomainMaps(
            AssessmentResponse rendered,
            Map<String, Double> domainWeights,
            Map<String, Integer> domainScores,
            Map<String, Double> weightedScores
    ) {
        double totalWeights = 0.0;
        if (rendered.segments() == null) {
            return totalWeights;
        }

        Map<String, Double> activeWeights = new LinkedHashMap<>();
        Map<String, Integer> activeScores = new LinkedHashMap<>();

        for (AssessmentResponse.SegmentScoreDto segment : rendered.segments()) {
            if (segment.segmentCode() == null
                    || !segment.segmentCode().toLowerCase(Locale.ROOT).startsWith("ndi_")) {
                continue;
            }
            boolean hasAnswered = segment.answers() != null && segment.answers().stream()
                    .anyMatch(AssessmentResponse.QuestionAnswerDto::answered);
            if (!hasAnswered) {
                continue;
            }
            String domainId = toNdiDomainId(segment.segmentCode());
            double weight = segment.weight() != null ? segment.weight() : 1.0;
            int score = (int) Math.round(segment.score());
            activeWeights.put(domainId, weight);
            activeScores.put(domainId, score);
            totalWeights += weight;
        }

        domainWeights.putAll(activeWeights);
        domainScores.putAll(activeScores);
        if (totalWeights > 0) {
            for (Map.Entry<String, Double> entry : activeWeights.entrySet()) {
                int score = activeScores.getOrDefault(entry.getKey(), 0);
                weightedScores.put(entry.getKey(), round3((score * entry.getValue()) / totalWeights));
            }
        }
        return totalWeights;
    }

    private static String toNdiDomainId(String segmentCode) {
        String lower = segmentCode.toLowerCase(Locale.ROOT).trim();
        if (lower.startsWith("ndi_")) {
            return lower.substring(4).toUpperCase(Locale.ROOT);
        }
        return segmentCode.toUpperCase(Locale.ROOT);
    }

    private static double round3(double value) {
        return Math.round(value * 1000.0) / 1000.0;
    }

    private static String buildReportFilename(String projectName, int version) {
        String slug = projectName == null ? "projet" : projectName.trim()
                .replaceAll("[^A-Za-z0-9_-]+", "-")
                .replaceAll("-{2,}", "-")
                .replaceAll("^-+|-+$", "");
        if (slug.isBlank()) {
            slug = "projet";
        }
        return "rapport-recommandations-" + slug + "-version-" + version + ".pdf";
    }

    public record RecommendationReportResult(byte[] pdfBytes, String filename) {
    }
}
