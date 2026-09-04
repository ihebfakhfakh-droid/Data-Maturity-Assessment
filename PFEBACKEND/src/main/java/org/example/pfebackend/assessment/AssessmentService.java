package org.example.pfebackend.assessment;

import org.example.pfebackend.assessment.dto.AssessmentResponse;
import org.example.pfebackend.assessment.dto.AssessmentVersionDiffDto;
import org.example.pfebackend.assessment.dto.AssessmentVersionSummaryDto;
import org.example.pfebackend.assessment.dto.CompareVersionsResponse;
import org.example.pfebackend.assessment.dto.MaturityLevel;
import org.example.pfebackend.assessment.dto.SubmitAnswersRequest;
import org.example.pfebackend.evidence.Evidence;
import org.example.pfebackend.evidence.EvidenceRating;
import org.example.pfebackend.project.ClientEntitlementService;
import org.example.pfebackend.project.ClientProjectEntitlements;
import org.example.pfebackend.project.Framework;
import org.example.pfebackend.project.Project;
import org.example.pfebackend.project.ProjectRepository;
import org.example.pfebackend.staff.StaffService;
import org.example.pfebackend.user.AppUser;
import org.example.pfebackend.user.AppUserRepository;
import org.example.pfebackend.user.Role;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.dao.DataIntegrityViolationException;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Service;
import org.springframework.transaction.PlatformTransactionManager;
import org.springframework.transaction.TransactionDefinition;
import org.springframework.transaction.annotation.Propagation;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.transaction.support.DefaultTransactionDefinition;
import org.springframework.transaction.support.TransactionTemplate;
import org.springframework.web.server.ResponseStatusException;

import java.sql.SQLException;
import java.time.Instant;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.HashMap;
import java.util.LinkedHashMap;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.Objects;
import java.util.Optional;
import java.util.Set;
import java.util.TreeSet;
import java.util.stream.Collectors;

@Service
public class AssessmentService {

    private static final Logger log = LoggerFactory.getLogger(AssessmentService.class);

    private final AssessmentRepository assessmentRepository;
    private final QuestionnaireQuestionRepository questionRepository;
    private final AssessmentAnswerRepository answerRepository;
    private final ClientEntitlementService entitlementService;
    private final AssessmentVersioningService assessmentVersioningService;
    private final AppUserRepository appUserRepository;
    private final ProjectRepository projectRepository;
    private final LegacyQuestionnaireMetadataService metadataService;
    private final StaffService staffService;
    /**
     * Each create attempt runs in its own transaction so a PostgreSQL unique-constraint failure
     * aborts only that transaction. Retries must not reuse an aborted transaction (see
     * createOrGetAssessmentForYear).
     */
    private final TransactionTemplate requiresNewTransactionTemplate;

    public AssessmentService(
            AssessmentRepository assessmentRepository,
            QuestionnaireQuestionRepository questionRepository,
            AssessmentAnswerRepository answerRepository,
            ClientEntitlementService entitlementService,
            PlatformTransactionManager transactionManager,
            AssessmentVersioningService assessmentVersioningService,
            AppUserRepository appUserRepository,
            ProjectRepository projectRepository,
            LegacyQuestionnaireMetadataService metadataService,
            StaffService staffService
    ) {
        this.assessmentRepository = assessmentRepository;
        this.questionRepository = questionRepository;
        this.answerRepository = answerRepository;
        this.entitlementService = entitlementService;
        this.assessmentVersioningService = assessmentVersioningService;
        this.appUserRepository = appUserRepository;
        this.projectRepository = projectRepository;
        this.metadataService = metadataService;
        this.staffService = staffService;
        DefaultTransactionDefinition txDef = new DefaultTransactionDefinition();
        txDef.setPropagationBehavior(TransactionDefinition.PROPAGATION_REQUIRES_NEW);
        this.requiresNewTransactionTemplate = new TransactionTemplate(transactionManager, txDef);
    }

    /**
     * Creates or returns the active assessment for the year. Uses an isolated transaction per attempt
     * so duplicate-key races (or {@code noRollbackFor}-style poisoned sessions on PostgreSQL) cannot
     * leave the connection in "transaction is aborted" state.
     * <p>{@link Propagation#NOT_SUPPORTED} ensures no outer transactional boundary (e.g. from another
     * service) reuses one Hibernate session across retries after a failed insert.
     */
    @Transactional(propagation = Propagation.NOT_SUPPORTED)
    public Assessment createOrGetAssessmentForYear(String clientEmail, int year) {
        String email = normalizeEmail(clientEmail);
        for (int attempt = 0; attempt < 6; attempt++) {
            try {
                return requiresNewTransactionTemplate.execute(status ->
                        createOrGetAssessmentForYearInOwnTransaction(email, year));
            } catch (RuntimeException e) {
                if (e instanceof ResponseStatusException) {
                    throw e;
                }
                if (shouldRetryAfterAssessmentCreateConflict(e)) {
                    continue;
                }
                throw e;
            }
        }
        throw new ResponseStatusException(HttpStatus.CONFLICT, "Could not create or load assessment after retries");
    }

    /**
     * Duplicate-key races are not always surfaced as {@link DataIntegrityViolationException}; Hibernate
     * may wrap PostgreSQL errors. After a failed {@code INSERT}, the same JDBC transaction can also yield
     * only "current transaction is aborted" on the next statement — treat as retryable for this flow.
     */
    private static boolean shouldRetryAfterAssessmentCreateConflict(Throwable ex) {
        if (ex instanceof DataIntegrityViolationException) {
            return true;
        }
        for (Throwable t = ex; t != null; t = t.getCause()) {
            if (t instanceof DataIntegrityViolationException) {
                return true;
            }
            if (t instanceof SQLException sql && "23505".equals(sql.getSQLState())) {
                return true;
            }
            String m = t.getMessage();
            if (m != null) {
                String ml = m.toLowerCase(Locale.ROOT);
                if (ml.contains("uq_assessment_client_year_version")
                        || ml.contains("duplicate key")
                        || ml.contains("clé dupliquée")
                        || ml.contains("transaction is aborted")
                        || ml.contains("transaction est annulée")) {
                    return true;
                }
            }
        }
        return false;
    }

    private Assessment createOrGetAssessmentForYearInOwnTransaction(String normalizedEmail, int year) {
        AppUser client = appUserRepository.findByEmailIgnoreCase(normalizedEmail)
                .orElseThrow(() -> new ResponseStatusException(HttpStatus.UNAUTHORIZED, "User not found"));

        Optional<Assessment> latestOpt =
                assessmentRepository.findFirstByClient_IdAndYearOrderByVersionDesc(client.getId(), year);

        if (latestOpt.isEmpty()) {
            Assessment created = new Assessment();
            created.setClient(client);
            created.setProject(requireLatestProject(client));
            created.setYear(year);
            created.setVersion(1);
            created.setStatus(AssessmentStatus.DRAFT);
            return assessmentRepository.saveAndFlush(created);
        }

        Assessment latest = latestOpt.get();
        ensureAssessmentProject(latest);
        if (latest.getStatus() == AssessmentStatus.DRAFT) {
            return latest;
        }

        if (latest.getStatus() == AssessmentStatus.SUBMITTED) {
            return latest;
        }

        throw new ResponseStatusException(
                HttpStatus.CONFLICT,
                "Unsupported assessment status for versioning: " + latest.getStatus()
        );
    }

    @Transactional
    public AssessmentResponse submitAnswers(Long assessmentId, String clientEmail, SubmitAnswersRequest request) {
        Assessment assessment = assessmentRepository.findById(assessmentId)
                .orElseThrow(() -> new ResponseStatusException(HttpStatus.NOT_FOUND, "Assessment not found"));

        String email = normalizeEmail(clientEmail);
        if (!assessment.getClient().getEmail().equalsIgnoreCase(email)) {
            throw new ResponseStatusException(HttpStatus.FORBIDDEN, "Not allowed");
        }
        ensureAssessmentProject(assessment);
        ClientProjectEntitlements entitlements = entitlementService.entitlementsForClientEmail(email);
        if (entitlements.isEmpty()) {
            throw new ResponseStatusException(HttpStatus.FORBIDDEN, "No frameworks assigned to this client");
        }
        if (assessment.getStatus() == AssessmentStatus.SUBMITTED) {
            if (!Boolean.TRUE.equals(request.forceNewVersion())) {
                // Idempotent submit: repeated clicks should not error.
                return buildAssessmentResponse(assessment);
            }
            Assessment latest = latestAssessmentForSameClientYear(assessment);
            if (!latest.getId().equals(assessment.getId())) {
                throw new ResponseStatusException(
                        HttpStatus.CONFLICT,
                        "Old assessment versions are read-only. Only the latest version can be modified."
                );
            }
            assessment = createDraftFromSubmitted(latest);
        } else if (assessment.getStatus() != AssessmentStatus.DRAFT) {
            throw new ResponseStatusException(HttpStatus.CONFLICT, "Assessment is not in current assessment state");
        }

        assertActiveDraft(assessment);
        saveAnswers(assessment, entitlements, request);
        carryForwardUntouchedSubmittedFrameworks(assessment, entitlements, request);
        assertAllAllowedQuestionsAnswered(assessment, entitlements);

        markSubmitted(assessment, assessment.getClient(), Instant.now(), request.versionComment());
        Assessment saved = assessmentRepository.save(assessment);
        answerRepository.flush();
        return buildAssessmentResponse(saved);
    }

    @Transactional
    public AssessmentResponse submitAnswersAsStaff(Long assessmentId, AppUser staff, SubmitAnswersRequest request) {
        Assessment assessment = assessmentRepository.findById(assessmentId)
                .orElseThrow(() -> new ResponseStatusException(HttpStatus.NOT_FOUND, "Assessment not found"));
        ensureAssessmentProject(assessment);
        ClientProjectEntitlements entitlements = entitlementService.entitlementsForClientEmail(assessment.getClient().getEmail());
        if (entitlements.isEmpty()) {
            throw new ResponseStatusException(HttpStatus.FORBIDDEN, "No frameworks assigned to this client");
        }

        if (assessment.getStatus() == AssessmentStatus.SUBMITTED) {
            Assessment latest = latestAssessmentForSameClientYear(assessment);
            if (!latest.getId().equals(assessment.getId())) {
                throw new ResponseStatusException(
                        HttpStatus.CONFLICT,
                        "Old assessment versions are read-only. Only the latest version can be modified."
                );
            }
            if (!hasEffectiveAnswerChanges(latest, entitlements, request) && !Boolean.TRUE.equals(request.forceNewVersion())) {
                markSubmitted(latest, staff, Instant.now(), request.versionComment());
                return buildAssessmentResponse(assessmentRepository.save(latest));
            }
            assessment = createDraftFromSubmitted(latest);
        } else if (assessment.getStatus() != AssessmentStatus.DRAFT) {
            throw new ResponseStatusException(HttpStatus.CONFLICT, "Assessment is not in current assessment state");
        }

        assertActiveDraft(assessment);
        saveAnswers(assessment, entitlements, request);
        carryForwardUntouchedSubmittedFrameworks(assessment, entitlements, request);
        assertAllAllowedQuestionsAnswered(assessment, entitlements);

        markSubmitted(assessment, staff, Instant.now(), request.versionComment());
        Assessment saved = assessmentRepository.save(assessment);
        answerRepository.flush();
        return buildAssessmentResponse(saved);
    }

    @Transactional
    public AssessmentResponse saveDraftAnswers(Long assessmentId, String clientEmail, SubmitAnswersRequest request) {
        Assessment assessment = assessmentRepository.findById(assessmentId)
                .orElseThrow(() -> new ResponseStatusException(HttpStatus.NOT_FOUND, "Assessment not found"));

        String email = normalizeEmail(clientEmail);
        if (!assessment.getClient().getEmail().equalsIgnoreCase(email)) {
            throw new ResponseStatusException(HttpStatus.FORBIDDEN, "Not allowed");
        }
        ensureAssessmentProject(assessment);
        ClientProjectEntitlements entitlements = entitlementService.entitlementsForClientEmail(email);
        if (entitlements.isEmpty()) {
            throw new ResponseStatusException(HttpStatus.FORBIDDEN, "No frameworks assigned to this client");
        }
        if (assessment.getStatus() == AssessmentStatus.SUBMITTED) {
            Assessment latest = latestAssessmentForSameClientYear(assessment);
            if (!latest.getId().equals(assessment.getId())) {
                throw new ResponseStatusException(
                        HttpStatus.CONFLICT,
                        "Old assessment versions are read-only. Only the latest version can be modified."
                );
            }
            if (latest.getStatus() == AssessmentStatus.SUBMITTED) {
                if (!hasEffectiveAnswerChanges(latest, entitlements, request)) {
                    return buildAssessmentResponse(latest);
                }
                assessment = createDraftFromSubmitted(latest);
            } else if (latest.getStatus() == AssessmentStatus.DRAFT) {
                assessment = latest;
            } else {
                throw new ResponseStatusException(
                        HttpStatus.CONFLICT,
                        "Unsupported assessment status for versioning: " + latest.getStatus()
                );
            }
        } else if (assessment.getStatus() != AssessmentStatus.DRAFT) {
            throw new ResponseStatusException(
                    HttpStatus.CONFLICT,
                    "Submitted assessment versions are frozen. Call POST /api/client/assessments to open the current assessment before saving answers."
            );
        }

        assertActiveDraft(assessment);
        if (!hasEffectiveAnswerChanges(assessment, entitlements, request)) {
            return buildAssessmentResponse(assessment);
        }
        saveAnswers(assessment, entitlements, request);
        answerRepository.flush();
        return buildAssessmentResponse(assessment);
    }

    private Assessment latestAssessmentForSameClientYear(Assessment assessment) {
        return assessmentRepository.findFirstByClient_IdAndYearOrderByVersionDesc(
                        assessment.getClient().getId(),
                        assessment.getYear()
                )
                .orElseThrow(() -> new ResponseStatusException(HttpStatus.NOT_FOUND, "Assessment not found"));
    }

    private Assessment createDraftFromSubmitted(Assessment submitted) {
        Assessment fork = new Assessment();
        fork.setClient(submitted.getClient());
        fork.setProject(submitted.getProject() != null ? submitted.getProject() : requireLatestProject(submitted.getClient()));
        fork.setYear(submitted.getYear());
        fork.setVersion(submitted.getVersion() + 1);
        fork.setStatus(AssessmentStatus.DRAFT);
        fork.setSubmittedAt(null);
        fork.setSubmittedBy(null);
        fork.setSubmittedByRole(null);
        fork.setVersionComment(null);
        Assessment savedFork = assessmentRepository.saveAndFlush(fork);
        assessmentVersioningService.copyAnswersAndEvidence(submitted, savedFork);
        return savedFork;
    }

    private void markSubmitted(Assessment assessment, AppUser submittedBy, Instant submittedAt, String versionComment) {
        assessment.setStatus(AssessmentStatus.SUBMITTED);
        assessment.setSubmittedAt(submittedAt);
        assessment.setSubmittedBy(submittedBy);
        assessment.setSubmittedByRole(submittedBy != null ? submittedBy.getRole() : null);
        assessment.setVersionComment(normalizeVersionComment(versionComment));
    }

    private static String normalizeVersionComment(String versionComment) {
        if (versionComment == null) {
            return null;
        }
        String trimmed = versionComment.trim();
        return trimmed.isEmpty() ? null : trimmed;
    }

    private Project requireLatestProject(AppUser client) {
        return projectRepository.findTopByClientOrderByCreatedAtDesc(client)
                .orElseThrow(() -> new ResponseStatusException(HttpStatus.FORBIDDEN, "No project assigned to this client"));
    }

    private void ensureAssessmentProject(Assessment assessment) {
        if (assessment.getProject() != null) {
            return;
        }
        assessment.setProject(requireLatestProject(assessment.getClient()));
        assessmentRepository.saveAndFlush(assessment);
    }

    private void assertActiveDraft(Assessment assessment) {
        Optional<Assessment> tip = assessmentRepository.findFirstByClient_IdAndYearOrderByVersionDesc(
                assessment.getClient().getId(),
                assessment.getYear()
        );
        if (tip.isEmpty() || !tip.get().getId().equals(assessment.getId())) {
            throw new ResponseStatusException(
                    HttpStatus.CONFLICT,
                    "This is not the active current assessment; create or open the assessment again to work on the latest version."
            );
        }
    }

    private void saveAnswers(Assessment assessment, ClientProjectEntitlements entitlements, SubmitAnswersRequest request) {
        // Load all questions to validate codes and allow partial draft saves.
        Map<String, QuestionnaireQuestion> questionsByCode = loadQuestionsByCode();

        for (SubmitAnswersRequest.AnswerItem item : request.answers()) {
            QuestionnaireQuestion q = requireAllowedQuestion(item, questionsByCode, entitlements);

            Boolean answeredFlag = item.answered();
            Integer submittedScore = item.score();
            String submittedComment = normalizeAnswerNote(item.comment());
            boolean explicitlyUnanswered = Boolean.FALSE.equals(answeredFlag)
                    && (submittedScore == null || submittedScore == 0);
            boolean explicitlyAnswered = Boolean.TRUE.equals(answeredFlag);
            boolean emptyAutosave = answeredFlag == null && (submittedScore == null || submittedScore == 0);

            if (explicitlyUnanswered || emptyAutosave) {
                answerRepository.findByAssessment_IdAndQuestion_Code(assessment.getId(), item.questionCode())
                        .ifPresent(existing -> {
                            if (!hasEvidences(existing)) {
                                answerRepository.delete(existing);
                            }
                        });
                continue;
            }
            if (submittedScore == null) {
                throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "score is required for answered question: " + item.questionCode());
            }
            boolean newAnswered = explicitlyAnswered || submittedScore > 0;

            AssessmentAnswer answer = answerRepository
                    .findByAssessment_IdAndQuestion_Code(assessment.getId(), item.questionCode())
                    .orElseGet(() -> {
                        AssessmentAnswer a = new AssessmentAnswer();
                        a.setAssessment(assessment);
                        a.setQuestion(q);
                        return a;
                    });

            if (answer.getId() == null
                    || answer.getScore() != submittedScore
                    || answer.isAnswered() != newAnswered
                    || !Objects.equals(normalizeAnswerNote(answer.getNote()), submittedComment)) {
                answer.setScore(submittedScore);
                answer.setAnswered(newAnswered);
                answer.setNote(submittedComment);
                answer.setAnsweredAt(Instant.now());
                answerRepository.save(answer);
            }
        }
    }

    private boolean hasEffectiveAnswerChanges(
            Assessment assessment,
            ClientProjectEntitlements entitlements,
            SubmitAnswersRequest request
    ) {
        Map<String, QuestionnaireQuestion> questionsByCode = loadQuestionsByCode();
        Map<String, AssessmentAnswer> answersByQuestionCode = answerRepository.findByAssessment_Id(assessment.getId()).stream()
                .collect(Collectors.toMap(a -> a.getQuestion().getCode(), a -> a, (a, b) -> a));

        for (SubmitAnswersRequest.AnswerItem item : request.answers()) {
            requireAllowedQuestion(item, questionsByCode, entitlements);

            Boolean answeredFlag = item.answered();
            Integer submittedScore = item.score();
            String submittedComment = normalizeAnswerNote(item.comment());
            boolean explicitlyUnanswered = Boolean.FALSE.equals(answeredFlag)
                    && (submittedScore == null || submittedScore == 0);
            boolean explicitlyAnswered = Boolean.TRUE.equals(answeredFlag);
            boolean emptyAutosave = answeredFlag == null && (submittedScore == null || submittedScore == 0);
            AssessmentAnswer existing = answersByQuestionCode.get(item.questionCode());

            if (explicitlyUnanswered || emptyAutosave) {
                if (existing != null && !hasEvidences(existing)) {
                    return true;
                }
                continue;
            }
            if (submittedScore == null) {
                throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "score is required for answered question: " + item.questionCode());
            }
            boolean newAnswered = explicitlyAnswered || submittedScore > 0;
            if (existing == null
                    || existing.getScore() != submittedScore
                    || existing.isAnswered() != newAnswered
                    || !Objects.equals(normalizeAnswerNote(existing.getNote()), submittedComment)) {
                return true;
            }
        }
        return false;
    }

    private static String normalizeAnswerNote(String note) {
        if (note == null) {
            return null;
        }
        String trimmed = note.trim();
        return trimmed.isEmpty() ? null : trimmed;
    }

    private Map<String, QuestionnaireQuestion> loadQuestionsByCode() {
        return questionRepository.findAll().stream()
                .collect(Collectors.toMap(QuestionnaireQuestion::getCode, q -> q, (a, b) -> a));
    }

    private QuestionnaireQuestion requireAllowedQuestion(
            SubmitAnswersRequest.AnswerItem item,
            Map<String, QuestionnaireQuestion> questionsByCode,
            ClientProjectEntitlements entitlements
    ) {
        QuestionnaireQuestion q = questionsByCode.get(item.questionCode());
        if (q == null) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "Unknown questionCode: " + item.questionCode());
        }
        if (!isQuestionAllowed(q, entitlements)) {
            throw new ResponseStatusException(HttpStatus.FORBIDDEN, "Question not allowed for assigned frameworks: " + item.questionCode());
        }
        return q;
    }

    private void assertAllAllowedQuestionsAnswered(Assessment assessment, ClientProjectEntitlements entitlements) {
        Map<String, Set<String>> requiredByFramework = requiredQuestionCodesByFramework(entitlements);
        Set<String> answeredQuestionCodes = answerRepository.findByAssessment_Id(assessment.getId()).stream()
                .filter(this::isAnswered)
                .map(a -> a.getQuestion().getCode())
                .collect(Collectors.toSet());

        List<FrameworkCompletion> frameworkCompletions = requiredByFramework.entrySet().stream()
                .map(entry -> {
                    Set<String> requiredCodes = entry.getValue();
                    int answeredQuestions = (int) requiredCodes.stream()
                            .filter(answeredQuestionCodes::contains)
                            .count();
                    int totalQuestions = requiredCodes.size();
                    return new FrameworkCompletion(
                            entry.getKey(),
                            totalQuestions,
                            answeredQuestions,
                            totalQuestions > 0 && answeredQuestions == totalQuestions
                    );
                })
                .toList();

        boolean allFrameworksComplete = frameworkCompletions.stream()
                .allMatch(FrameworkCompletion::isComplete);
        if (!allFrameworksComplete) {
            throw new ResponseStatusException(
                    HttpStatus.CONFLICT,
                    "Impossible de soumettre : tous les frameworks doivent être complétés."
            );
        }
    }

    private void carryForwardUntouchedSubmittedFrameworks(
            Assessment assessment,
            ClientProjectEntitlements entitlements,
            SubmitAnswersRequest request
    ) {
        Optional<Assessment> previousSubmitted = assessmentRepository
                .findByClient_IdAndYearOrderByVersionAsc(assessment.getClient().getId(), assessment.getYear())
                .stream()
                .filter(a -> a.getStatus() == AssessmentStatus.SUBMITTED)
                .filter(a -> a.getVersion() < assessment.getVersion())
                .max(Comparator.comparingInt(Assessment::getVersion));
        if (previousSubmitted.isEmpty()) {
            return;
        }

        Set<String> touchedFrameworks = request.answers().stream()
                .map(SubmitAnswersRequest.AnswerItem::questionCode)
                .map(AssessmentService::frameworkTagForQuestionCode)
                .filter(Objects::nonNull)
                .collect(Collectors.toCollection(LinkedHashSet::new));
        Set<String> frameworksToCarryForward = completedFrameworkTags(previousSubmitted.get(), entitlements);
        frameworksToCarryForward.retainAll(new LinkedHashSet<>(frameworkTags(entitlements)));
        frameworksToCarryForward.removeAll(touchedFrameworks);
        assessmentVersioningService.copyMissingAnswersAndEvidence(
                previousSubmitted.get(),
                assessment,
                frameworksToCarryForward
        );
    }

    private boolean isAnswered(AssessmentAnswer answer) {
        return answer.isAnswered();
    }

    private List<QuestionnaireQuestion> allowedActiveQuestions(ClientProjectEntitlements entitlements) {
        ClientProjectEntitlements e = entitlements == null || entitlements.isEmpty()
                ? new ClientProjectEntitlements(java.util.EnumSet.allOf(Framework.class), Set.of())
                : entitlements;
        return questionRepository.findByActiveTrueOrderBySegment_SortOrderAscSegment_CodeAscSortOrderAsc()
                .stream()
                .filter(q -> isQuestionAllowed(q, e))
                .sorted(QuestionnaireOrdering.questionComparator())
                .toList();
    }

    @Transactional(readOnly = true)
    public AssessmentResponse getAssessment(Long assessmentId, String clientEmail) {
        Assessment assessment = assessmentRepository.findById(assessmentId)
                .orElseThrow(() -> new ResponseStatusException(HttpStatus.NOT_FOUND, "Assessment not found"));

        String email = normalizeEmail(clientEmail);
        if (!assessment.getClient().getEmail().equalsIgnoreCase(email)) {
            throw new ResponseStatusException(HttpStatus.FORBIDDEN, "Not allowed");
        }

        assessment = assessmentRepository.findFirstByClient_IdAndYearOrderByVersionDesc(
                assessment.getClient().getId(),
                assessment.getYear()
        ).orElse(assessment);

        return buildAssessmentResponse(assessment);
    }

    @Transactional(readOnly = true)
    public AssessmentResponse getAssessmentVersionForClient(Long assessmentId, String clientEmail) {
        Assessment assessment = assessmentRepository.findById(assessmentId)
                .orElseThrow(() -> new ResponseStatusException(HttpStatus.NOT_FOUND, "Assessment not found"));

        String email = normalizeEmail(clientEmail);
        if (!assessment.getClient().getEmail().equalsIgnoreCase(email)) {
            throw new ResponseStatusException(HttpStatus.FORBIDDEN, "Assessment version does not belong to the connected client");
        }

        return buildAssessmentResponse(assessment);
    }

    @Transactional(readOnly = true)
    public AssessmentResponse getAssessmentAsAdmin(Long assessmentId) {
        Assessment assessment = assessmentRepository.findById(assessmentId)
                .orElseThrow(() -> new ResponseStatusException(HttpStatus.NOT_FOUND, "Assessment not found"));
        return buildAssessmentResponse(assessment);
    }

    @Transactional(readOnly = true)
    public AssessmentResponse renderAssessment(Assessment assessment) {
        return buildAssessmentResponse(assessment);
    }

    private AssessmentResponse buildAssessmentResponse(Assessment assessment) {
        List<AssessmentAnswer> answers = answerRepository.findByAssessment_Id(assessment.getId());
        Map<String, AssessmentAnswer> answersByQuestionCode = answers.stream()
                .collect(Collectors.toMap(a -> a.getQuestion().getCode(), a -> a, (a, b) -> a));

        // Group by the logical domain code, not only by the JPA segment relation.
        // If sub_domain links were damaged in PostgreSQL, built-in domains can still be separated from question codes.
        record QuestionAnswer(
                QuestionnaireQuestion q,
                int score,
                String note,
                List<Evidence> evidences,
                EvidenceRating evidenceStaffRating,
                String evidenceStaffComment,
                Instant answeredAt,
                boolean answered
        ) {}
        Map<String, List<QuestionAnswer>> bySegment = new LinkedHashMap<>();
        if (assessment.getStatus() == AssessmentStatus.DRAFT) {
            ClientProjectEntitlements entitlements = entitlementService.entitlementsForClientEmail(assessment.getClient().getEmail());
            List<QuestionnaireQuestion> questions = allowedActiveQuestions(entitlements);
            for (QuestionnaireQuestion q : questions) {
                AssessmentAnswer a = answersByQuestionCode.get(q.getCode());
                bySegment.computeIfAbsent(assessmentSegmentCodeFor(q), s -> new ArrayList<>())
                        .add(new QuestionAnswer(
                                q,
                                a != null ? a.getScore() : 0,
                                a != null ? a.getNote() : null,
                                evidencesFor(a),
                                effectiveEvidenceStaffRating(a),
                                a != null ? a.getEvidenceStaffComment() : null,
                                a != null ? a.getAnsweredAt() : null,
                                a != null && isAnswered(a)
                        ));
            }
        } else {
            for (AssessmentAnswer a : answers) {
                QuestionnaireQuestion q = a.getQuestion();
                bySegment.computeIfAbsent(assessmentSegmentCodeFor(q), s -> new ArrayList<>())
                        .add(new QuestionAnswer(q, a.getScore(), a.getNote(), evidencesFor(a), effectiveEvidenceStaffRating(a), a.getEvidenceStaffComment(), a.getAnsweredAt(), isAnswered(a)));
            }
        }

        boolean anyCustomZeroFive = bySegment.values().stream()
                .map(qs -> qs.get(0).q().getSegment())
                .anyMatch(seg -> seg != null && seg.getMaturityFramework() != null
                        && seg.getMaturityFramework().getScoreScale() == FrameworkScoreScale.ZERO_TO_FIVE);

        List<AssessmentResponse.SegmentScoreDto> segmentDtos = bySegment.entrySet().stream()
                .sorted(Comparator
                        .comparingInt((Map.Entry<String, List<QuestionAnswer>> e) ->
                                QuestionnaireOrdering.segmentSortOrder(e.getValue().get(0).q()))
                        .thenComparing(Map.Entry::getKey))
                .map(entry -> {
                    List<QuestionAnswer> qs = entry.getValue().stream()
                            .sorted(Comparator.comparing(QuestionAnswer::q, QuestionnaireOrdering.questionComparator()))
                            .toList();
                    QuestionnaireSegment segment = qs.get(0).q().getSegment();
                    List<QuestionAnswer> answeredQs = qs.stream()
                            .filter(QuestionAnswer::answered)
                            .toList();
                    int answeredQuestions = answeredQs.size();
                    int totalQuestions = qs.size();

                    MaturityFrameworkDefinition mf = segment != null ? segment.getMaturityFramework() : null;
                    String segmentCode = entry.getKey();
                    int aggregateScore;
                    if (answeredQs.isEmpty()) {
                        aggregateScore = 0;
                    } else if (mf == null || mf.getDomainScoringMethod() == DomainScoringMethod.DOMAIN_MINIMUM) {
                        aggregateScore = answeredQs.stream().mapToInt(QuestionAnswer::score).min().orElse(0);
                    } else {
                        aggregateScore = (int) Math.round(answeredQs.stream().mapToInt(QuestionAnswer::score).average().orElse(0));
                    }
                    int clampedDomainScore = answeredQs.isEmpty()
                            ? 0
                            : mf != null
                                    ? clampForCustomScale(mf.getScoreScale(), aggregateScore)
                                    : clampScoreForSegment(segmentCode, aggregateScore);
                    double segmentScore = clampedDomainScore;
                    Double domainAverageScore = answeredQs.isEmpty()
                            ? null
                            : round2(answeredQs.stream().mapToInt(QuestionAnswer::score).average().orElse(0.0));
                    String label = answeredQs.isEmpty()
                            ? "Not answered"
                            : mf != null
                                    ? labelForCustomScale(mf.getScoreScale(), clampedDomainScore)
                                    : frameworkLabel(segmentCode, clampedDomainScore);

                    List<AssessmentResponse.QuestionAnswerDto> questionDtos = qs.stream()
                            .map(x -> {
                                String answerLabel = x.answered()
                                        ? mf != null
                                                ? labelForCustomScale(mf.getScoreScale(), x.score())
                                                : frameworkLabel(segmentCode, x.score())
                                        : "Not answered";
                                List<AssessmentResponse.EvidenceDto> evidenceDtos = x.evidences().stream()
                                        .map(AssessmentService::toEvidenceDto)
                                        .toList();
                                Evidence firstEvidence = x.evidences().isEmpty() ? null : x.evidences().get(0);
                                Long evidenceId = firstEvidence != null ? firstEvidence.getId() : null;
                                return new AssessmentResponse.QuestionAnswerDto(
                                        x.q().getId(),
                                        x.q().getCode(),
                                        x.q().getText(),
                                        x.score(),
                                        answerLabel,
                                        x.note(),
                                        x.answeredAt(),
                                        evidenceId,
                                        evidenceId != null ? "/api/client/evidences/" + evidenceId + "/download" : null,
                                        firstEvidence != null ? firstEvidence.getOriginalFileName() : null,
                                        x.evidenceStaffRating(),
                                        x.evidenceStaffComment(),
                                        evidenceDtos,
                                        x.answered()
                                );
                            })
                            .toList();

                    return new AssessmentResponse.SegmentScoreDto(
                            assessmentSegmentIdFor(qs.get(0).q(), segmentCode),
                            segmentCode,
                            metadataService.titleFor(qs.get(0).q()),
                            round2(segmentScore),
                            domainAverageScore,
                            label,
                            answeredQuestions,
                            totalQuestions,
                            totalQuestions > 0 && answeredQuestions == totalQuestions,
                            domainWeightFor(qs.get(0).q()),
                            questionDtos
                    );
                })
                .toList();

        int answeredQuestions = bySegment.values().stream()
                .flatMap(List::stream)
                .filter(QuestionAnswer::answered)
                .mapToInt(q -> 1)
                .sum();
        int totalQuestions = bySegment.values().stream().mapToInt(List::size).sum();
        boolean complete = totalQuestions > 0 && answeredQuestions == totalQuestions;
        int progressPercent = totalQuestions == 0 ? 0 : (int) Math.round(answeredQuestions * 100.0 / totalQuestions);
        double domainGlobalScore = weightedSegmentScore(segmentDtos);
        double domainGlobalAverageScore = weightedSegmentAverageScore(segmentDtos);
        boolean canSubmit = assessment.getStatus() == AssessmentStatus.DRAFT && complete;
        ClientProjectEntitlements responseEntitlements = entitlementService.entitlementsForClientEmail(assessment.getClient().getEmail());
        List<AssessmentResponse.FrameworkStatusDto> frameworkStatus = buildFrameworkStatus(
                assessment,
                responseEntitlements,
                segmentDtos,
                answers
        );
        String globalStatus = frameworkStatus.stream().allMatch(f -> AssessmentStatus.SUBMITTED.name().equals(f.frameworkStatus()))
                ? AssessmentStatus.SUBMITTED.name()
                : AssessmentStatus.DRAFT.name();
        double globalScore = domainGlobalScore;
        int globalRounded = clampGlobalRounded(segmentDtos, (int) Math.round(globalScore), anyCustomZeroFive);
        boolean anyAnswered = answeredQuestions > 0;
        String globalLabel = anyAnswered
                ? mixedGlobalLabel(segmentDtos, globalRounded, anyCustomZeroFive)
                : "Not answered";

        return new AssessmentResponse(
                assessment.getId(),
                assessment.getYear(),
                assessment.getVersion(),
                assessment.getVersion(),
                assessment.getStatus().name(),
                globalStatus,
                assessment.getClient().getId(),
                assessment.getClient().getFullName(),
                assessment.getClient().getEmail(),
                assessment.getCreatedAt(),
                assessment.getSubmittedAt(),
                assessment.getSubmittedBy() != null ? assessment.getSubmittedBy().getId() : null,
                assessment.getSubmittedBy() != null ? assessment.getSubmittedBy().getFullName() : null,
                assessment.getSubmittedBy() != null ? assessment.getSubmittedBy().getEmail() : null,
                assessment.getSubmittedByRole() != null ? assessment.getSubmittedByRole().name() : null,
                assessment.getVersionComment(),
                assessment.getRecommendationTargetScore(),
                round2(globalScore),
                round2(domainGlobalAverageScore),
                globalLabel,
                answeredQuestions,
                totalQuestions,
                complete,
                canSubmit,
                progressPercent,
                workflowStatus(assessment.getStatus(), anyAnswered),
                frameworkStatus,
                segmentDtos
        );
    }

    private static boolean hasEvidences(AssessmentAnswer answer) {
        return answer != null && answer.getEvidences() != null && !answer.getEvidences().isEmpty();
    }

    private static List<Evidence> evidencesFor(AssessmentAnswer answer) {
        if (answer == null || answer.getEvidences() == null) {
            return List.of();
        }
        return answer.getEvidences().stream()
                .sorted(Comparator
                        .comparing(Evidence::getCreatedAt, Comparator.nullsLast(Instant::compareTo))
                        .thenComparing(Evidence::getId, Comparator.nullsLast(Long::compareTo)))
                .toList();
    }

    private static EvidenceRating effectiveEvidenceStaffRating(AssessmentAnswer answer) {
        if (answer == null) {
            return null;
        }
        if (answer.getEvidenceStaffRating() != null) {
            return answer.getEvidenceStaffRating();
        }
        return evidencesFor(answer).stream()
                .map(Evidence::getStaffRating)
                .filter(Objects::nonNull)
                .findFirst()
                .orElse(null);
    }

    private static AssessmentResponse.EvidenceDto toEvidenceDto(Evidence evidence) {
        String downloadUrl = "/api/client/evidences/" + evidence.getId() + "/download";
        return new AssessmentResponse.EvidenceDto(
                evidence.getId(),
                evidence.getOriginalFileName(),
                downloadUrl,
                downloadUrl,
                evidence.getCreatedAt()
        );
    }

    private List<AssessmentResponse.FrameworkStatusDto> buildFrameworkStatus(
            Assessment assessment,
            ClientProjectEntitlements entitlements,
            List<AssessmentResponse.SegmentScoreDto> segmentDtos,
            List<AssessmentAnswer> answers
    ) {
        List<Assessment> versions = assessmentRepository.findByClient_IdAndYearOrderByVersionAsc(
                assessment.getClient().getId(),
                assessment.getYear()
        );
        List<String> activeFrameworks = frameworkTags(entitlements);
        Set<String> displayedFrameworks = displayedFrameworkTags(assessment, versions, activeFrameworks, answers);
        Map<String, Set<String>> requiredByFramework = requiredQuestionCodesByFramework(entitlements);
        Set<String> answeredQuestionCodes = answers.stream()
                .filter(this::isAnswered)
                .map(a -> a.getQuestion().getCode())
                .collect(Collectors.toSet());

        return displayedFrameworks.stream()
                .map(frameworkCode -> {
                    Set<String> requiredCodes = requiredByFramework.getOrDefault(frameworkCode, Set.of());
                    int totalQuestions = requiredCodes.size();
                    int answeredQuestions = (int) requiredCodes.stream()
                            .filter(answeredQuestionCodes::contains)
                            .count();
                    boolean complete = totalQuestions > 0 && answeredQuestions == totalQuestions;
                    Instant frameworkSubmittedAt = submittedAtForFramework(
                            frameworkCode,
                            assessment.getVersion(),
                            versions,
                            entitlements
                    );
                    Instant frameworkAnswerSubmittedAt = submittedAnswerAtForFramework(
                            frameworkCode,
                            assessment.getVersion(),
                            versions
                    );
                    boolean submitted = frameworkSubmittedAt != null
                            || frameworkAnswerSubmittedAt != null
                            || assessment.getStatus() == AssessmentStatus.SUBMITTED
                            || complete;
                    Instant lastSubmissionDate = latestInstant(
                            frameworkSubmittedAt,
                            frameworkAnswerSubmittedAt,
                            submitted ? assessment.getSubmittedAt() : null
                    );
                    return new AssessmentResponse.FrameworkStatusDto(
                            frameworkCode,
                            submitted ? AssessmentStatus.SUBMITTED.name() : AssessmentStatus.DRAFT.name(),
                            frameworkScore(frameworkCode, segmentDtos),
                            frameworkAverageScore(frameworkCode, segmentDtos),
                            answeredQuestions,
                            totalQuestions,
                            complete,
                            lastSubmissionDate,
                            lastSubmissionDate
                    );
                })
                .toList();
    }

    private Set<String> displayedFrameworkTags(
            Assessment assessment,
            List<Assessment> versions,
            List<String> activeFrameworks,
            List<AssessmentAnswer> answers
    ) {
        int latestVersion = versions.stream()
                .mapToInt(Assessment::getVersion)
                .max()
                .orElse(assessment.getVersion());
        Set<String> tags = new LinkedHashSet<>();
        if (assessment.getVersion() == latestVersion) {
            tags.addAll(activeFrameworks);
        } else {
            tags.addAll(frameworkTagsFromAnswers(answers));
        }
        if (tags.isEmpty()) {
            tags.addAll(activeFrameworks);
        }

        Set<String> ordered = new LinkedHashSet<>();
        for (String framework : activeFrameworks) {
            if (tags.contains(framework)) {
                ordered.add(framework);
            }
        }
        tags.stream()
                .filter(tag -> !ordered.contains(tag))
                .sorted()
                .forEach(ordered::add);
        return ordered;
    }

    private Set<String> frameworkTagsFromAnswers(List<AssessmentAnswer> answers) {
        return answers.stream()
                .map(a -> frameworkTagForQuestionCode(a.getQuestion().getCode()))
                .filter(Objects::nonNull)
                .collect(Collectors.toCollection(LinkedHashSet::new));
    }

    private Instant submittedAtForFramework(
            String frameworkCode,
            int maxVersionInclusive,
            List<Assessment> versions,
            ClientProjectEntitlements entitlements
    ) {
        return versions.stream()
                .filter(a -> a.getVersion() <= maxVersionInclusive)
                .filter(a -> a.getStatus() == AssessmentStatus.SUBMITTED)
                .filter(a -> completedFrameworkTags(a, entitlements).contains(frameworkCode)
                        || frameworkTagsFromAnswers(answerRepository.findByAssessment_Id(a.getId())).contains(frameworkCode))
                .map(Assessment::getSubmittedAt)
                .filter(Objects::nonNull)
                .max(Comparator.naturalOrder())
                .orElse(null);
    }

    private Instant submittedAnswerAtForFramework(
            String frameworkCode,
            int maxVersionInclusive,
            List<Assessment> versions
    ) {
        return versions.stream()
                .filter(a -> a.getVersion() <= maxVersionInclusive)
                .filter(a -> a.getStatus() == AssessmentStatus.SUBMITTED)
                .flatMap(a -> answerRepository.findByAssessment_Id(a.getId()).stream())
                .filter(this::isAnswered)
                .filter(a -> Objects.equals(frameworkCode, frameworkTagForQuestionCode(a.getQuestion().getCode())))
                .map(AssessmentAnswer::getAnsweredAt)
                .filter(Objects::nonNull)
                .max(Comparator.naturalOrder())
                .orElse(null);
    }

    private static Instant latestInstant(Instant... values) {
        return java.util.Arrays.stream(values)
                .filter(Objects::nonNull)
                .max(Comparator.naturalOrder())
                .orElse(null);
    }

    private static Double frameworkScore(String frameworkCode, List<AssessmentResponse.SegmentScoreDto> segmentDtos) {
        List<AssessmentResponse.SegmentScoreDto> scores = segmentDtos.stream()
                .filter(segment -> Objects.equals(frameworkCode, frameworkTagForSegmentCode(segment.segmentCode())))
                .toList();
        if (scores.isEmpty()) {
            return null;
        }
        return round2(weightedSegmentScore(scores));
    }

    private static Double frameworkAverageScore(String frameworkCode, List<AssessmentResponse.SegmentScoreDto> segmentDtos) {
        List<AssessmentResponse.SegmentScoreDto> scores = segmentDtos.stream()
                .filter(segment -> Objects.equals(frameworkCode, frameworkTagForSegmentCode(segment.segmentCode())))
                .toList();
        if (scores.isEmpty() || scores.stream().noneMatch(segment -> segment.averageScore() != null)) {
            return null;
        }
        return round2(weightedSegmentAverageScore(scores));
    }

    private static double weightedSegmentScore(List<AssessmentResponse.SegmentScoreDto> segmentDtos) {
        double weightedTotal = 0.0;
        double totalWeight = 0.0;
        for (AssessmentResponse.SegmentScoreDto segment : segmentDtos) {
            double weight = normalizedDomainWeight(segment.weight());
            weightedTotal += segment.score() * weight;
            totalWeight += weight;
        }
        return totalWeight > 0 ? weightedTotal / totalWeight : 0.0;
    }

    private static double weightedSegmentAverageScore(List<AssessmentResponse.SegmentScoreDto> segmentDtos) {
        double weightedTotal = 0.0;
        double totalWeight = 0.0;
        for (AssessmentResponse.SegmentScoreDto segment : segmentDtos) {
            Double averageScore = segment.averageScore();
            if (averageScore == null) {
                continue;
            }
            double weight = normalizedDomainWeight(segment.weight());
            weightedTotal += averageScore * weight;
            totalWeight += weight;
        }
        return totalWeight > 0 ? weightedTotal / totalWeight : 0.0;
    }

    private static double normalizedDomainWeight(Double weight) {
        return weight != null && Double.isFinite(weight) && weight > 0 ? weight : 1.0;
    }

    private static String frameworkTagForSegmentCode(String segmentCode) {
        return frameworkTagForQuestionCode(segmentCode);
    }

    private static String assessmentSegmentCodeFor(QuestionnaireQuestion q) {
        String questionCode = q.getCode();
        if (questionCode != null && (questionCode.startsWith("ndi_") || questionCode.startsWith("cmmi_"))) {
            return QuestionnaireOrdering.segmentCodeFor(q);
        }
        QuestionnaireSegment segment = q.getSegment();
        if (segment != null && segment.getCode() != null && !segment.getCode().isBlank()) {
            return segment.getCode();
        }
        if (segment != null && segment.getId() != null) {
            return "sub_domain_" + segment.getId();
        }
        return QuestionnaireOrdering.segmentCodeFor(q);
    }

    private static String assessmentSegmentIdFor(QuestionnaireQuestion q, String segmentCode) {
        QuestionnaireSegment segment = q.getSegment();
        if (segment != null && segment.getId() != null) {
            return String.valueOf(segment.getId());
        }
        return segmentCode;
    }

    private static Double domainWeightFor(QuestionnaireQuestion q) {
        if (q == null) {
            return null;
        }
        QuestionnaireSegment segment = q.getSegment();
        if (segment != null && segment.getWeight() != null) {
            return segment.getWeight();
        }
        QuestionnaireDomain domain = q.getDomain();
        if (domain != null) {
            return domain.getWeight();
        }
        return segment != null && segment.getDomain() != null ? segment.getDomain().getWeight() : null;
    }

    @Transactional(readOnly = true)
    public List<Map<String, Object>> listMainAssessmentSummariesForClient(AppUser client) {
        Map<Long, List<Map<String, Object>>> assignedStaffByProjectId = new HashMap<>();
        return assessmentRepository.findByClientOrderByYearDescVersionDesc(client).stream()
                .collect(Collectors.groupingBy(Assessment::getYear, LinkedHashMap::new, Collectors.toList()))
                .values()
                .stream()
                .map(versions -> toMainAssessmentSummary(versions, assignedStaffByProjectId))
                .toList();
    }

    private Map<String, Object> toMainAssessmentSummary(
            List<Assessment> versions,
            Map<Long, List<Map<String, Object>>> assignedStaffByProjectId
    ) {
        Assessment assessment = versions.stream()
                .max(Comparator.comparingInt(Assessment::getVersion))
                .orElseThrow(() -> new ResponseStatusException(HttpStatus.NOT_FOUND, "Assessment not found"));
        Assessment latestSubmitted = versions.stream()
                .filter(version -> version.getStatus() == AssessmentStatus.SUBMITTED)
                .max(Comparator.comparingInt(Assessment::getVersion))
                .orElse(null);
        AssessmentResponse r = buildAssessmentResponse(assessment);
        Map<String, Object> m = new LinkedHashMap<>();
        m.put("id", assessment.getId());
        m.put("assessmentId", assessment.getId());
        m.put("client", clientSummary(assessment.getClient()));
        Project project = assessment.getProject();
        List<Map<String, Object>> assignedStaff = resolveAssignedStaffForProject(project, assignedStaffByProjectId);
        m.put("project", projectSummary(project, assignedStaff));
        m.put("year", assessment.getYear());
        m.put("version", assessment.getVersion());
        m.put("versionNumber", assessment.getVersion());
        m.put("currentVersion", assessment.getVersion());
        // globalStatus drives list badges/filters; entityStatus is the persisted row status.
        m.put("status", r.globalStatus());
        m.put("globalStatus", r.globalStatus());
        m.put("entityStatus", assessment.getStatus().name());
        m.put("isSubmitted", assessment.isSubmitted());
        if (latestSubmitted != null) {
            m.put("latestSubmittedAssessmentId", latestSubmitted.getId());
            m.put("latestSubmittedVersion", latestSubmitted.getVersion());
        }
        m.put("createdAt", assessment.getCreatedAt());
        m.put("submittedAt", assessment.getSubmittedAt());
        m.put("frameworks", r.frameworkStatus().stream().map(AssessmentResponse.FrameworkStatusDto::frameworkCode).toList());
        m.put("frameworkTags", r.frameworkStatus().stream().map(AssessmentResponse.FrameworkStatusDto::frameworkCode).toList());
        m.put("frameworkStatus", r.frameworkStatus());
        m.put("submittedFrameworks", r.frameworkStatus().stream()
                .filter(f -> AssessmentStatus.SUBMITTED.name().equals(f.frameworkStatus()))
                .map(AssessmentResponse.FrameworkStatusDto::frameworkCode)
                .toList());
        m.put("draftFrameworks", r.frameworkStatus().stream()
                .filter(f -> !AssessmentStatus.SUBMITTED.name().equals(f.frameworkStatus()))
                .map(AssessmentResponse.FrameworkStatusDto::frameworkCode)
                .toList());
        m.put("globalScore", r.globalScore());
        m.put("globalAverageScore", r.globalAverageScore());
        m.put("globalMaturityLabel", r.globalMaturityLabel());
        m.put("answeredQuestions", r.answeredQuestions());
        m.put("totalQuestions", r.totalQuestions());
        m.put("complete", r.complete());
        m.put("progressPercent", r.progressPercent());
        m.put("workflowStatus", r.globalStatus());
        putAssignedStaffFields(m, assignedStaff);
        return m;
    }

    private List<Map<String, Object>> resolveAssignedStaffForProject(
            Project project,
            Map<Long, List<Map<String, Object>>> assignedStaffByProjectId
    ) {
        if (project == null || project.getId() == null) {
            return List.of();
        }
        Long projectId = project.getId();
        return assignedStaffByProjectId.computeIfAbsent(
                projectId,
                id -> toAssignedStaffDtos(staffService.assignedStaffForProject(id))
        );
    }

    private static List<Map<String, Object>> toAssignedStaffDtos(List<Map<String, Object>> rows) {
        if (rows == null || rows.isEmpty()) {
            return List.of();
        }
        List<Map<String, Object>> out = new ArrayList<>(rows.size());
        for (Map<String, Object> row : rows) {
            Map<String, Object> staff = new LinkedHashMap<>();
            staff.put("id", row.get("id"));
            String fullName = row.get("fullName") != null ? String.valueOf(row.get("fullName")).trim() : "";
            staff.put("fullName", fullName.isEmpty() ? null : fullName);
            staff.put("email", row.get("email"));
            Object role = row.get("role");
            staff.put("role", role == null ? null : String.valueOf(role));
            String[] parts = fullName.isEmpty() ? new String[0] : fullName.split("\\s+", 2);
            staff.put("firstName", parts.length > 0 ? parts[0] : "");
            staff.put("lastName", parts.length > 1 ? parts[1] : "");
            out.add(staff);
        }
        return out;
    }

    private static void putAssignedStaffFields(Map<String, Object> target, List<Map<String, Object>> assignedStaff) {
        List<String> names = assignedStaff.stream()
                .map(row -> {
                    Object fullName = row.get("fullName");
                    if (fullName != null && !String.valueOf(fullName).isBlank()) {
                        return String.valueOf(fullName).trim();
                    }
                    String fromParts = (Objects.toString(row.get("firstName"), "") + " "
                            + Objects.toString(row.get("lastName"), "")).trim();
                    if (!fromParts.isEmpty()) {
                        return fromParts;
                    }
                    Object email = row.get("email");
                    return email == null ? null : String.valueOf(email).trim();
                })
                .filter(Objects::nonNull)
                .filter(s -> !s.isBlank())
                .toList();
        String label = names.isEmpty() ? null : String.join(", ", names);
        target.put("assignedStaff", assignedStaff);
        target.put("projectConsultants", assignedStaff);
        target.put("consultants", assignedStaff);
        target.put("assignedStaffNames", names);
        target.put("projectConsultantNames", names);
        target.put("assignedConsultantName", label);
        target.put("consultantName", label);
    }

    private MainAssessmentState buildMainAssessmentState(Assessment current, List<Assessment> versions) {
        ClientProjectEntitlements entitlements = entitlementService.entitlementsForClientEmail(current.getClient().getEmail());
        List<String> frameworks = frameworkTags(entitlements);
        Set<String> activeFrameworks = new LinkedHashSet<>(frameworks);
        Set<String> submittedFrameworks = versions.stream()
                .filter(a -> a.getStatus() == AssessmentStatus.SUBMITTED)
                .max(Comparator.comparingInt(Assessment::getVersion))
                .map(a -> completedFrameworkTags(a, entitlements))
                .orElseGet(LinkedHashSet::new);
        submittedFrameworks.retainAll(activeFrameworks);

        Set<String> draftFrameworks = new LinkedHashSet<>(activeFrameworks);
        draftFrameworks.removeAll(submittedFrameworks);
        if (current.getStatus() == AssessmentStatus.DRAFT && draftFrameworks.isEmpty()) {
            draftFrameworks = new LinkedHashSet<>(activeFrameworks);
            submittedFrameworks = new LinkedHashSet<>();
        }

        String globalStatus = draftFrameworks.isEmpty() && current.getStatus() == AssessmentStatus.SUBMITTED
                ? AssessmentStatus.SUBMITTED.name()
                : AssessmentStatus.DRAFT.name();

        if (AssessmentStatus.SUBMITTED.name().equals(globalStatus)) {
            submittedFrameworks = new LinkedHashSet<>(activeFrameworks);
            draftFrameworks = new LinkedHashSet<>();
        }

        return new MainAssessmentState(
                frameworks,
                orderedFrameworkSubset(frameworks, submittedFrameworks),
                orderedFrameworkSubset(frameworks, draftFrameworks),
                globalStatus
        );
    }

    private Set<String> completedFrameworkTags(Assessment assessment, ClientProjectEntitlements entitlements) {
        Map<String, Set<String>> requiredByFramework = requiredQuestionCodesByFramework(entitlements);
        Set<String> answeredQuestionCodes = answerRepository.findByAssessment_Id(assessment.getId()).stream()
                .filter(this::isAnswered)
                .map(a -> a.getQuestion().getCode())
                .collect(Collectors.toSet());
        Set<String> completed = new LinkedHashSet<>();
        for (Map.Entry<String, Set<String>> entry : requiredByFramework.entrySet()) {
            Set<String> requiredCodes = entry.getValue();
            if (!requiredCodes.isEmpty() && answeredQuestionCodes.containsAll(requiredCodes)) {
                completed.add(entry.getKey());
            }
        }
        return completed;
    }

    private Map<String, Set<String>> requiredQuestionCodesByFramework(ClientProjectEntitlements entitlements) {
        Map<String, Set<String>> out = new LinkedHashMap<>();
        for (String tag : frameworkTags(entitlements)) {
            out.put(tag, new LinkedHashSet<>());
        }
        for (QuestionnaireQuestion q : allowedActiveQuestions(entitlements)) {
            String tag = frameworkTagForQuestion(q);
            if (tag != null && out.containsKey(tag)) {
                out.get(tag).add(q.getCode());
            }
        }
        return out;
    }

    private static String frameworkTagForQuestion(QuestionnaireQuestion q) {
        return frameworkTagForQuestionCode(q.getCode());
    }

    private static String frameworkTagForQuestionCode(String code) {
        if (code == null) {
            return null;
        }
        String normalized = code.toLowerCase(Locale.ROOT);
        if (normalized.startsWith("ndi_")) {
            return Framework.NDI.name();
        }
        if (normalized.startsWith("cmmi_")) {
            return Framework.CMMI.name();
        }
        return null;
    }

    private static List<String> orderedFrameworkSubset(List<String> order, Set<String> values) {
        return order.stream()
                .filter(values::contains)
                .toList();
    }

    private static Map<String, Object> clientSummary(AppUser client) {
        Map<String, Object> m = new LinkedHashMap<>();
        m.put("id", client.getId());
        m.put("fullName", client.getFullName());
        m.put("email", client.getEmail());
        return m;
    }

    private static Map<String, Object> projectSummary(Project project) {
        return projectSummary(project, List.of());
    }

    private static Map<String, Object> projectSummary(Project project, List<Map<String, Object>> assignedStaff) {
        if (project == null) {
            return null;
        }
        Map<String, Object> m = new LinkedHashMap<>();
        m.put("id", project.getId());
        m.put("name", project.getName());
        putAssignedStaffFields(m, assignedStaff == null ? List.of() : assignedStaff);
        return m;
    }

    private record MainAssessmentState(
            List<String> frameworks,
            List<String> submittedFrameworks,
            List<String> draftFrameworks,
            String globalStatus
    ) {}

    private record FrameworkCompletion(
            String framework,
            int totalQuestions,
            int answeredQuestions,
            boolean isComplete
    ) {}

    @Transactional(readOnly = true)
    public List<AssessmentVersionSummaryDto> listVersionSummariesForClientYear(Long clientId, int year) {
        AppUser client = appUserRepository.findById(clientId)
                .orElseThrow(() -> new ResponseStatusException(HttpStatus.NOT_FOUND, "Client not found"));
        if (client.getRole() != Role.CLIENT) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "Not a client user");
        }
        return assessmentRepository.findByClient_IdAndYearOrderByVersionAsc(clientId, year).stream()
                .map(this::toVersionSummary)
                .toList();
    }

    @Transactional(readOnly = true)
    public List<AssessmentVersionSummaryDto> listVersionSummariesForConnectedClient(String clientEmail, Integer year) {
        String normalizedEmail = normalizeEmail(clientEmail);
        AppUser client = appUserRepository.findByEmailIgnoreCase(normalizedEmail)
                .orElseThrow(() -> new ResponseStatusException(HttpStatus.UNAUTHORIZED, "User not found"));
        if (client.getRole() != Role.CLIENT) {
            throw new ResponseStatusException(HttpStatus.FORBIDDEN, "Client access only");
        }
        List<Assessment> versions = year == null
                ? assessmentRepository.findByClient_IdOrderByYearAscVersionAsc(client.getId())
                : assessmentRepository.findByClient_IdAndYearOrderByVersionAsc(client.getId(), year);
        log.info(
                "Client assessment versions lookup: email={}, clientId={}, year={}, versionsFound={}",
                normalizedEmail,
                client.getId(),
                year == null ? "ALL" : year,
                versions.size()
        );
        return versions.stream()
                .map(this::toVersionSummary)
                .toList();
    }

    private AssessmentVersionSummaryDto toVersionSummary(Assessment a) {
        AssessmentResponse r = buildAssessmentResponse(a);
        List<String> versionFrameworkTags = r.frameworkStatus().stream()
                .map(AssessmentResponse.FrameworkStatusDto::frameworkCode)
                .toList();
        return new AssessmentVersionSummaryDto(
                a.getId(),
                a.getYear(),
                a.getVersion(),
                a.getVersion(),
                r.globalStatus(),
                r.globalStatus(),
                a.getCreatedAt(),
                a.getSubmittedAt(),
                a.getVersionComment(),
                r.globalScore(),
                r.globalAverageScore(),
                r.globalMaturityLabel(),
                versionFrameworkTags,
                r.frameworkStatus(),
                r.frameworkStatus(),
                r.answeredQuestions(),
                r.totalQuestions(),
                r.complete(),
                r.progressPercent(),
                r.globalStatus()
        );
    }

    @Transactional(readOnly = true)
    public AssessmentVersionDiffDto diffFromPreviousVersion(Long assessmentId) {
        Assessment newer = assessmentRepository.findById(assessmentId)
                .orElseThrow(() -> new ResponseStatusException(HttpStatus.NOT_FOUND, "Assessment not found"));
        if (newer.getVersion() <= 1) {
            throw new ResponseStatusException(HttpStatus.NOT_FOUND, "No previous version to compare");
        }
        Assessment older = assessmentRepository
                .findByClient_IdAndYearAndVersion(
                        newer.getClient().getId(),
                        newer.getYear(),
                        newer.getVersion() - 1
                )
                .orElseThrow(() -> new ResponseStatusException(HttpStatus.NOT_FOUND, "Previous assessment version not found"));

        return buildDiffBetweenAssessments(older, newer);
    }

    /**
     * Compare deux versions (même client, même année). {@code fromVersion} doit être &lt; {@code toVersion}.
     */
    @Transactional(readOnly = true)
    public CompareVersionsResponse compareVersionsForClientYear(Long clientId, int year, int fromVersion, int toVersion) {
        if (fromVersion >= toVersion) {
            throw new ResponseStatusException(
                    HttpStatus.BAD_REQUEST,
                    "fromVersion must be strictly less than toVersion (compare chronologically)."
            );
        }
        Assessment older = assessmentRepository
                .findByClient_IdAndYearAndVersion(clientId, year, fromVersion)
                .orElseThrow(() -> new ResponseStatusException(HttpStatus.NOT_FOUND, "Assessment version not found: " + fromVersion));
        Assessment newer = assessmentRepository
                .findByClient_IdAndYearAndVersion(clientId, year, toVersion)
                .orElseThrow(() -> new ResponseStatusException(HttpStatus.NOT_FOUND, "Assessment version not found: " + toVersion));
        if (!older.getClient().getId().equals(clientId) || !newer.getClient().getId().equals(clientId)) {
            throw new ResponseStatusException(HttpStatus.NOT_FOUND, "Assessment not found for this client");
        }
        if (older.getYear() != year || newer.getYear() != year) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "Year mismatch");
        }
        AssessmentVersionDiffDto raw = buildDiffBetweenAssessments(older, newer);
        return toCompareVersionsResponse(older, newer, raw);
    }

    /**
     * Compare deux évaluations par identifiants (même client). Les versions peuvent être non consécutives.
     */
    @Transactional(readOnly = true)
    public CompareVersionsResponse compareByAssessmentIds(Long clientId, Long fromAssessmentId, Long toAssessmentId) {
        if (fromAssessmentId.equals(toAssessmentId)) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "fromAssessmentId and toAssessmentId must differ");
        }
        Assessment a1 = assessmentRepository.findById(fromAssessmentId)
                .orElseThrow(() -> new ResponseStatusException(HttpStatus.NOT_FOUND, "Assessment not found: " + fromAssessmentId));
        Assessment a2 = assessmentRepository.findById(toAssessmentId)
                .orElseThrow(() -> new ResponseStatusException(HttpStatus.NOT_FOUND, "Assessment not found: " + toAssessmentId));
        if (!a1.getClient().getId().equals(clientId) || !a2.getClient().getId().equals(clientId)) {
            throw new ResponseStatusException(HttpStatus.NOT_FOUND, "Assessment not found for this client");
        }
        if (a1.getYear() != a2.getYear()) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "Assessments must be for the same year");
        }
        Assessment older = a1.getVersion() <= a2.getVersion() ? a1 : a2;
        Assessment newer = a1.getVersion() <= a2.getVersion() ? a2 : a1;
        if (older.getVersion() == newer.getVersion()) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "Same version number on both assessments");
        }
        AssessmentVersionDiffDto raw = buildDiffBetweenAssessments(older, newer);
        return toCompareVersionsResponse(older, newer, raw);
    }

    private AssessmentVersionDiffDto buildDiffBetweenAssessments(Assessment older, Assessment newer) {
        AssessmentResponse o = buildAssessmentResponse(older);
        AssessmentResponse n = buildAssessmentResponse(newer);
        Map<String, QuestionnaireQuestion> questionsByCode = questionRepository.findAll().stream()
                .collect(Collectors.toMap(QuestionnaireQuestion::getCode, q -> q, (a, b) -> a));

        Map<String, AssessmentResponse.QuestionAnswerDto> oldQ = flattenQuestions(o);
        Map<String, AssessmentResponse.QuestionAnswerDto> newQ = flattenQuestions(n);
        Set<String> codes = new TreeSet<>();
        codes.addAll(oldQ.keySet());
        codes.addAll(newQ.keySet());

        List<AssessmentVersionDiffDto.AnswerDiff> answerDiffs = new ArrayList<>();
        List<AssessmentVersionDiffDto.EvidenceDiff> evidenceDiffs = new ArrayList<>();

        for (String code : codes) {
            AssessmentResponse.QuestionAnswerDto oa = oldQ.get(code);
            AssessmentResponse.QuestionAnswerDto na = newQ.get(code);
            Integer oScore = oa != null ? oa.score() : null;
            Integer nScore = na != null ? na.score() : null;
            String oLab = oa != null ? oa.maturityLabel() : null;
            String nLab = na != null ? na.maturityLabel() : null;
            if (!Objects.equals(oScore, nScore) || !Objects.equals(oLab, nLab)) {
                QuestionnaireQuestion qDef = questionsByCode.get(code);
                String qText = qDef != null ? qDef.getText() : (na != null ? na.questionText() : (oa != null ? oa.questionText() : code));
                String segCode = null;
                String segTitle = null;
                String parentCode = null;
                String parentTitle = null;
                if (qDef != null) {
                    QuestionnaireSegment seg = qDef.getSegment();
                    segCode = QuestionnaireOrdering.segmentCodeFor(qDef);
                    segTitle = seg != null ? seg.getTitle() : metadataService.titleFor(qDef);
                } else if (na != null) {
                    segCode = segmentMetaForQuestion(code, n).segmentCode();
                    segTitle = segmentMetaForQuestion(code, n).segmentTitle();
                } else if (oa != null) {
                    segCode = segmentMetaForQuestion(code, o).segmentCode();
                    segTitle = segmentMetaForQuestion(code, o).segmentTitle();
                }
                answerDiffs.add(new AssessmentVersionDiffDto.AnswerDiff(
                        code,
                        qText,
                        segCode,
                        segTitle,
                        parentCode,
                        parentTitle,
                        oScore,
                        nScore,
                        oLab,
                        nLab
                ));
            }

            String oName = oa != null ? oa.evidenceFileName() : null;
            String nName = na != null ? na.evidenceFileName() : null;
            EvidenceRating oRate = oa != null ? oa.evidenceStaffRating() : null;
            EvidenceRating nRate = na != null ? na.evidenceStaffRating() : null;
            Long oId = oa != null ? oa.evidenceId() : null;
            Long nId = na != null ? na.evidenceId() : null;

            boolean hadFile = oName != null && !oName.isBlank();
            boolean hasFile = nName != null && !nName.isBlank();
            if (!hadFile && !hasFile && Objects.equals(oRate, nRate)) {
                continue;
            }
            if (hadFile && hasFile && Objects.equals(oName, nName) && Objects.equals(oRate, nRate)) {
                continue;
            }
            if (!hadFile && hasFile) {
                evidenceDiffs.add(new AssessmentVersionDiffDto.EvidenceDiff(
                        code, "ADDED", null, nName, null, nId, null, nRate, null, null
                ));
            } else if (hadFile && !hasFile) {
                evidenceDiffs.add(new AssessmentVersionDiffDto.EvidenceDiff(
                        code, "REMOVED", oName, null, oId, null, oRate, null, null, null
                ));
            } else if (hadFile && hasFile && !Objects.equals(oName, nName)) {
                evidenceDiffs.add(new AssessmentVersionDiffDto.EvidenceDiff(
                        code, "FILE_REPLACED", oName, nName, oId, nId, oRate, nRate, null, null
                ));
            } else if (hadFile && hasFile && !Objects.equals(oRate, nRate)) {
                evidenceDiffs.add(new AssessmentVersionDiffDto.EvidenceDiff(
                        code, "RATING_CHANGED", oName, nName, oId, nId, oRate, nRate, null, null
                ));
            }
        }

        Map<String, AssessmentResponse.SegmentScoreDto> oldSeg = flattenSegments(o);
        Map<String, AssessmentResponse.SegmentScoreDto> newSeg = flattenSegments(n);
        Set<String> segCodes = new TreeSet<>();
        segCodes.addAll(oldSeg.keySet());
        segCodes.addAll(newSeg.keySet());
        List<AssessmentVersionDiffDto.SegmentScoreDiff> segmentDiffs = new ArrayList<>();
        for (String sc : segCodes) {
            AssessmentResponse.SegmentScoreDto os = oldSeg.get(sc);
            AssessmentResponse.SegmentScoreDto ns = newSeg.get(sc);
            double osv = os != null ? os.score() : Double.NaN;
            double nsv = ns != null ? ns.score() : Double.NaN;
            String ol = os != null ? os.maturityLabel() : null;
            String nl = ns != null ? ns.maturityLabel() : null;
            if (scoresDiffer(osv, nsv) || !Objects.equals(ol, nl)) {
                String parentCode = null;
                String parentTitle = null;
                segmentDiffs.add(new AssessmentVersionDiffDto.SegmentScoreDiff(
                        sc,
                        os != null ? os.segmentTitle() : (ns != null ? ns.segmentTitle() : sc),
                        parentCode,
                        parentTitle,
                        os != null ? round2(osv) : null,
                        ns != null ? round2(nsv) : null,
                        ol,
                        nl
                ));
            }
        }

        AssessmentVersionDiffDto.GlobalScoreDiff global = new AssessmentVersionDiffDto.GlobalScoreDiff(
                round2(o.globalScore()),
                round2(n.globalScore()),
                o.globalMaturityLabel(),
                n.globalMaturityLabel()
        );

        return new AssessmentVersionDiffDto(
                older.getVersion(),
                newer.getVersion(),
                global,
                segmentDiffs,
                answerDiffs,
                evidenceDiffs
        );
    }

    private static CompareVersionsResponse toCompareVersionsResponse(
            Assessment older,
            Assessment newer,
            AssessmentVersionDiffDto raw
    ) {
        List<CompareVersionsResponse.AnswerChange> changedAnswers = raw.answers().stream()
                .map(a -> new CompareVersionsResponse.AnswerChange(
                        a.questionCode(),
                        a.questionText(),
                        a.segmentCode(),
                        a.segmentTitle(),
                        a.parentSegmentCode(),
                        a.parentSegmentTitle(),
                        a.oldScore(),
                        a.newScore(),
                        a.oldMaturityLabel(),
                        a.newMaturityLabel()
                ))
                .toList();

        List<CompareVersionsResponse.EvidenceChange> changedEvidences = raw.evidences().stream()
                .map(e -> new CompareVersionsResponse.EvidenceChange(
                        e.questionCode(),
                        e.changeType(),
                        e.oldFileName(),
                        e.newFileName(),
                        e.oldEvidenceId(),
                        e.newEvidenceId(),
                        e.oldStaffRating(),
                        e.newStaffRating()
                ))
                .toList();

        AssessmentVersionDiffDto.GlobalScoreDiff g = raw.globalScore();
        List<CompareVersionsResponse.SegmentScoreChange> segChanges = raw.segmentScores().stream()
                .map(s -> new CompareVersionsResponse.SegmentScoreChange(
                        s.segmentCode(),
                        s.segmentTitle(),
                        s.parentSegmentCode(),
                        s.parentSegmentTitle(),
                        s.oldScore(),
                        s.newScore(),
                        s.oldMaturityLabel(),
                        s.newMaturityLabel()
                ))
                .toList();
        CompareVersionsResponse.ChangedScores changedScores = new CompareVersionsResponse.ChangedScores(
                g.oldScore(),
                g.newScore(),
                g.oldLabel(),
                g.newLabel(),
                segChanges
        );

        List<CompareVersionsResponse.ChangeItem> added = new ArrayList<>();
        List<CompareVersionsResponse.ChangeItem> removed = new ArrayList<>();
        List<CompareVersionsResponse.ChangeItem> modified = new ArrayList<>();

        for (AssessmentVersionDiffDto.EvidenceDiff e : raw.evidences()) {
            switch (e.changeType()) {
                case "ADDED" -> added.add(new CompareVersionsResponse.ChangeItem(
                        "EVIDENCE",
                        e.questionCode(),
                        "Evidence",
                        "Fichier ajouté: " + (e.newFileName() != null ? e.newFileName() : "")
                ));
                case "REMOVED" -> removed.add(new CompareVersionsResponse.ChangeItem(
                        "EVIDENCE",
                        e.questionCode(),
                        "Evidence",
                        "Fichier retiré: " + (e.oldFileName() != null ? e.oldFileName() : "")
                ));
                case "FILE_REPLACED", "RATING_CHANGED" -> modified.add(new CompareVersionsResponse.ChangeItem(
                        "EVIDENCE",
                        e.questionCode(),
                        "Evidence",
                        e.changeType() + " — "
                                + (e.oldFileName() != null ? e.oldFileName() : "")
                                + " → "
                                + (e.newFileName() != null ? e.newFileName() : "")
                ));
                default -> {
                }
            }
        }

        for (AssessmentVersionDiffDto.AnswerDiff a : raw.answers()) {
            if (a.oldScore() == null && a.newScore() != null) {
                added.add(new CompareVersionsResponse.ChangeItem(
                        "ANSWER",
                        a.questionCode(),
                        a.questionText(),
                        "Nouvelle réponse, score=" + a.newScore()
                ));
            } else if (a.oldScore() != null && a.newScore() == null) {
                removed.add(new CompareVersionsResponse.ChangeItem(
                        "ANSWER",
                        a.questionCode(),
                        a.questionText(),
                        "Réponse supprimée (ancien score=" + a.oldScore() + ")"
                ));
            } else {
                modified.add(new CompareVersionsResponse.ChangeItem(
                        "ANSWER",
                        a.questionCode(),
                        a.questionText(),
                        "Score " + a.oldScore() + " → " + a.newScore()
                ));
            }
        }

        for (AssessmentVersionDiffDto.SegmentScoreDiff s : raw.segmentScores()) {
            modified.add(new CompareVersionsResponse.ChangeItem(
                    "SEGMENT",
                    s.segmentCode(),
                    s.segmentTitle(),
                    "Score domaine "
                            + (s.oldScore() != null ? s.oldScore() : "—")
                            + " → "
                            + (s.newScore() != null ? s.newScore() : "—")
            ));
        }

        if (raw.globalScore() != null
                && (!Objects.equals(raw.globalScore().oldScore(), raw.globalScore().newScore())
                || !Objects.equals(raw.globalScore().oldLabel(), raw.globalScore().newLabel()))) {
            modified.add(new CompareVersionsResponse.ChangeItem(
                    "GLOBAL",
                    "GLOBAL",
                    "Score global",
                    (raw.globalScore().oldScore() != null ? raw.globalScore().oldScore() : "—")
                            + " ("
                            + raw.globalScore().oldLabel()
                            + ") → "
                            + (raw.globalScore().newScore() != null ? raw.globalScore().newScore() : "—")
                            + " ("
                            + raw.globalScore().newLabel()
                            + ")"
            ));
        }

        return new CompareVersionsResponse(
                older.getVersion(),
                newer.getVersion(),
                older.getId(),
                newer.getId(),
                changedScores,
                changedAnswers,
                changedEvidences,
                added,
                removed,
                modified
        );
    }

    private static boolean scoresDiffer(double a, double b) {
        if (Double.isNaN(a) && Double.isNaN(b)) {
            return false;
        }
        if (Double.isNaN(a) || Double.isNaN(b)) {
            return true;
        }
        return Math.abs(a - b) > 0.001;
    }

    private static Map<String, AssessmentResponse.QuestionAnswerDto> flattenQuestions(AssessmentResponse r) {
        Map<String, AssessmentResponse.QuestionAnswerDto> m = new LinkedHashMap<>();
        for (AssessmentResponse.SegmentScoreDto seg : r.segments()) {
            for (AssessmentResponse.QuestionAnswerDto q : seg.answers()) {
                m.put(q.questionCode(), q);
            }
        }
        return m;
    }

    private static Map<String, AssessmentResponse.SegmentScoreDto> flattenSegments(AssessmentResponse r) {
        Map<String, AssessmentResponse.SegmentScoreDto> m = new LinkedHashMap<>();
        for (AssessmentResponse.SegmentScoreDto seg : r.segments()) {
            m.put(seg.segmentCode(), seg);
        }
        return m;
    }

    private static SegmentMeta segmentMetaForQuestion(String questionCode, AssessmentResponse r) {
        for (AssessmentResponse.SegmentScoreDto seg : r.segments()) {
            for (AssessmentResponse.QuestionAnswerDto q : seg.answers()) {
                if (questionCode.equals(q.questionCode())) {
                    return new SegmentMeta(seg.segmentCode(), seg.segmentTitle());
                }
            }
        }
        return new SegmentMeta(null, null);
    }

    private record SegmentMeta(String segmentCode, String segmentTitle) {}

    private static List<String> frameworkTags(ClientProjectEntitlements e) {
        List<String> t = new ArrayList<>();
        for (Framework f : e.builtinFrameworks()) {
            t.add(f.name());
        }
        for (Long id : e.customMaturityFrameworkIds()) {
            t.add("CUSTOM_" + id);
        }
        t.sort(Comparator.naturalOrder());
        return t;
    }

    private static String workflowStatus(AssessmentStatus status, boolean anyAnswered) {
        if (status == AssessmentStatus.SUBMITTED) {
            return "SUBMITTED";
        }
        return anyAnswered ? "IN_PROGRESS" : "DRAFT";
    }

    private static double round2(double v) {
        return Math.round(v * 100.0) / 100.0;
    }

    private static boolean isNdiSegment(String segmentCode) {
        return segmentCode != null && segmentCode.startsWith("ndi_");
    }

    private static boolean isCmmiSegment(String segmentCode) {
        return segmentCode != null && segmentCode.startsWith("cmmi_");
    }

    /**
     * Labels requested for the UI (French wording kept close to the spec).
     */
    private static String ndiLabel(int score) {
        return switch (score) {
            case 0 -> "Absence of capabilities";
            case 1 -> "Establishing";
            case 2 -> "Defined";
            case 3 -> "Activated";
            case 4 -> "Managed";
            case 5 -> "Pioneer";
            default -> "—";
        };
    }

    private static String cmmiLabel(int score) {
        return switch (score) {
            case 1 -> "Performed";
            case 2 -> "Managed";
            case 3 -> "Defined";
            case 4 -> "Measured";
            case 5 -> "Optimized";
            default -> "—";
        };
    }

    private static String frameworkLabel(String segmentCode, int score) {
        int s = Math.min(5, Math.max(0, score));
        if (isNdiSegment(segmentCode)) {
            return ndiLabel(s);
        }
        if (isCmmiSegment(segmentCode)) {
            // CMMI scale is 1..5 in this project; clamp 0 to 1 for display if it ever appears.
            int cmmi = Math.min(5, Math.max(1, s == 0 ? 1 : s));
            return cmmiLabel(cmmi);
        }
        // Fallback: generic 1..5 scale
        int g = Math.min(5, Math.max(1, s == 0 ? 1 : s));
        return MaturityLevel.fromScore(g).labelFr();
    }

    private static int clampScoreForSegment(String segmentCode, int score) {
        if (isNdiSegment(segmentCode)) {
            return Math.min(5, Math.max(0, score));
        }
        if (isCmmiSegment(segmentCode)) {
            return Math.min(5, Math.max(1, score));
        }
        return Math.min(5, Math.max(1, score));
    }

    private static int clampForCustomScale(FrameworkScoreScale scale, int score) {
        if (scale == FrameworkScoreScale.ZERO_TO_FIVE) {
            return Math.min(5, Math.max(0, score));
        }
        return Math.min(5, Math.max(1, score));
    }

    private static String labelForCustomScale(FrameworkScoreScale scale, int score) {
        int s = scale == FrameworkScoreScale.ZERO_TO_FIVE
                ? Math.min(5, Math.max(0, score))
                : Math.min(5, Math.max(1, score == 0 ? 1 : score));
        if (scale == FrameworkScoreScale.ZERO_TO_FIVE) {
            return ndiLabel(s);
        }
        return cmmiLabel(s);
    }

    private static int clampGlobalRounded(List<AssessmentResponse.SegmentScoreDto> segments, int roundedGlobal, boolean anyCustomZeroFive) {
        boolean anyNdi = segments.stream().anyMatch(s -> isNdiSegment(s.segmentCode()));
        boolean anyCmmi = segments.stream().anyMatch(s -> isCmmiSegment(s.segmentCode()));
        if (anyCmmi) {
            return Math.min(5, Math.max(1, roundedGlobal));
        }
        if (anyNdi || anyCustomZeroFive) {
            return Math.min(5, Math.max(0, roundedGlobal));
        }
        return Math.min(5, Math.max(1, roundedGlobal));
    }

    private static String mixedGlobalLabel(List<AssessmentResponse.SegmentScoreDto> segments, int roundedGlobal, boolean anyCustomZeroFive) {
        boolean anyNdi = segments.stream().anyMatch(s -> isNdiSegment(s.segmentCode()));
        boolean anyCmmi = segments.stream().anyMatch(s -> isCmmiSegment(s.segmentCode()));
        if (anyCmmi && !anyNdi) {
            int g = Math.min(5, Math.max(1, roundedGlobal == 0 ? 1 : roundedGlobal));
            return cmmiLabel(g);
        }
        if (!anyCmmi && (anyNdi || anyCustomZeroFive)) {
            return ndiLabel(Math.min(5, Math.max(0, roundedGlobal)));
        }
        int g = Math.min(5, Math.max(1, roundedGlobal == 0 ? 1 : roundedGlobal));
        return MaturityLevel.fromScore(g).labelFr();
    }

    private static String normalizeEmail(String email) {
        return email == null ? "" : email.trim().toLowerCase(Locale.ROOT);
    }

    private static boolean isQuestionAllowed(QuestionnaireQuestion q, ClientProjectEntitlements e) {
        String questionCode = q.getCode();
        if (questionCode == null) {
            return false;
        }
        if (questionCode.startsWith("ndi_")) {
            return e.builtinFrameworks().contains(Framework.NDI);
        }
        if (questionCode.startsWith("cmmi_")) {
            return e.builtinFrameworks().contains(Framework.CMMI);
        }
        return !e.builtinFrameworks().isEmpty();
    }

}

