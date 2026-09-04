package org.example.pfebackend.evidence;

import org.example.pfebackend.assessment.Assessment;
import org.example.pfebackend.assessment.AssessmentAnswer;
import org.example.pfebackend.assessment.AssessmentAnswerRepository;
import org.example.pfebackend.assessment.AssessmentRepository;
import org.example.pfebackend.assessment.AssessmentStatus;
import org.example.pfebackend.assessment.QuestionnaireQuestion;
import org.example.pfebackend.assessment.QuestionnaireQuestionRepository;
import org.example.pfebackend.evidence.dto.EvidenceUploadResponse;
import org.example.pfebackend.evidence.dto.RateEvidenceRequest;
import org.example.pfebackend.staff.StaffService;
import org.example.pfebackend.user.AppUser;
import org.example.pfebackend.user.CommittedAppUserLoader;
import org.example.pfebackend.user.Role;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.web.multipart.MultipartFile;
import org.springframework.web.server.ResponseStatusException;

import java.io.InputStream;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.StandardCopyOption;
import java.time.Instant;
import java.util.Arrays;
import java.util.List;
import java.util.Locale;
import java.util.Objects;
import java.util.UUID;

@Service
public class EvidenceService {

    private final Path rootDir;
    private final EvidenceRepository evidenceRepository;
    private final AssessmentRepository assessmentRepository;
    private final AssessmentAnswerRepository answerRepository;
    private final QuestionnaireQuestionRepository questionRepository;
    private final CommittedAppUserLoader committedAppUserLoader;
    private final StaffService staffService;

    public EvidenceService(
            @Value("${app.evidence.storage-dir:./data/evidence}") String storageDir,
            EvidenceRepository evidenceRepository,
            AssessmentRepository assessmentRepository,
            AssessmentAnswerRepository answerRepository,
            QuestionnaireQuestionRepository questionRepository,
            CommittedAppUserLoader committedAppUserLoader,
            StaffService staffService
    ) {
        this.rootDir = Path.of(storageDir);
        this.evidenceRepository = evidenceRepository;
        this.assessmentRepository = assessmentRepository;
        this.answerRepository = answerRepository;
        this.questionRepository = questionRepository;
        this.committedAppUserLoader = committedAppUserLoader;
        this.staffService = staffService;
    }

    @Transactional
    public List<EvidenceUploadResponse> uploadEvidencesForAnswer(
            Long assessmentId,
            String clientEmail,
            String questionCode,
            int score,
            MultipartFile[] files
    ) {
        List<MultipartFile> uploadFiles = normalizeFiles(files);
        return uploadFiles.stream()
                .map(file -> uploadEvidenceForAnswer(assessmentId, clientEmail, questionCode, score, file))
                .toList();
    }

    @Transactional
    public EvidenceUploadResponse uploadEvidenceForAnswer(
            Long assessmentId,
            String clientEmail,
            String questionCode,
            int score,
            MultipartFile file
    ) {
        if (file == null || file.isEmpty()) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "File is required");
        }
        if (score < 0 || score > 5) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "Score must be between 0 and 5");
        }

        Assessment assessment = assessmentRepository.findById(assessmentId)
                .orElseThrow(() -> new ResponseStatusException(HttpStatus.NOT_FOUND, "Assessment not found"));

        String email = normalizeEmail(clientEmail);
        if (!assessment.getClient().getEmail().equalsIgnoreCase(email)) {
            throw new ResponseStatusException(HttpStatus.FORBIDDEN, "Not allowed");
        }
        Assessment targetAssessment = latestAssessmentForEvidence(assessment);

        QuestionnaireQuestion question = questionRepository.findByCode(questionCode)
                .orElseThrow(() -> new ResponseStatusException(HttpStatus.BAD_REQUEST, "Unknown questionCode: " + questionCode));

        AssessmentAnswer answer = answerRepository.findByAssessment_IdAndQuestion_Code(targetAssessment.getId(), questionCode)
                .orElseGet(() -> {
                    AssessmentAnswer a = new AssessmentAnswer();
                    a.setAssessment(targetAssessment);
                    a.setQuestion(question);
                    a.setScore(score);
                    return answerRepository.save(a);
                });
        answer.setScore(score);
        answer.setAnswered(true);
        answer.setAnsweredAt(Instant.now());
        answerRepository.save(answer);

        AppUser uploader = committedAppUserLoader.findByEmailInNewTransaction(email)
                .orElseThrow(() -> new ResponseStatusException(HttpStatus.UNAUTHORIZED, "User not found"));

        Evidence ev = new Evidence();
        ev.setAnswer(answer);
        ev.setUploadedBy(uploader);
        ev.setOriginalFileName(safeFileName(file.getOriginalFilename()));
        ev.setContentType(normalizeContentType(file.getContentType()));
        ev.setSizeBytes(file.getSize());

        // Store file on disk first (new UUID per upload to avoid conflicts)
        String evidenceKey = UUID.randomUUID().toString();
        String relative = evidenceKey + "/" + ev.getOriginalFileName();
        Path target = rootDir.resolve(relative).normalize();
        ensureUnderRoot(target);

        try {
            Files.createDirectories(target.getParent());
            try (InputStream in = file.getInputStream()) {
                Files.copy(in, target, StandardCopyOption.REPLACE_EXISTING);
            }
        } catch (Exception e) {
            throw new ResponseStatusException(HttpStatus.INTERNAL_SERVER_ERROR, "Failed to store file");
        }

        ev.setStoragePath(relative);
        Evidence saved = evidenceRepository.save(ev);

        return new EvidenceUploadResponse(
                saved.getId(),
                targetAssessment.getId(),
                saved.getOriginalFileName(),
                saved.getContentType(),
                saved.getSizeBytes(),
                effectiveStaffRating(answer, saved),
                saved.getCreatedAt()
        );
    }

    private Assessment latestAssessmentForEvidence(Assessment requested) {
        Assessment latest = assessmentRepository.findFirstByClient_IdAndYearOrderByVersionDesc(
                        requested.getClient().getId(),
                        requested.getYear()
                )
                .orElse(requested);
        if (latest.getStatus() != AssessmentStatus.SUBMITTED) {
            return latest;
        }

        Assessment fork = new Assessment();
        fork.setClient(latest.getClient());
        fork.setProject(latest.getProject());
        fork.setYear(latest.getYear());
        fork.setVersion(latest.getVersion() + 1);
        fork.setStatus(AssessmentStatus.DRAFT);
        Assessment savedFork = assessmentRepository.saveAndFlush(fork);
        copyAnswersAndEvidence(latest, savedFork);
        return savedFork;
    }

    private void copyAnswersAndEvidence(Assessment source, Assessment target) {
        List<AssessmentAnswer> sourceAnswers = answerRepository.findByAssessment_Id(source.getId());
        for (AssessmentAnswer src : sourceAnswers) {
            AssessmentAnswer copied = new AssessmentAnswer();
            copied.setAssessment(target);
            copied.setQuestion(src.getQuestion());
            copied.setScore(src.getScore());
            copied.setAnswered(src.isAnswered());
            copied.setNote(src.getNote());
            copied.setAnsweredAt(src.getAnsweredAt() != null ? src.getAnsweredAt() : Instant.now());
            copied.setEvidenceStaffRating(src.getEvidenceStaffRating());
            copied.setEvidenceStaffComment(src.getEvidenceStaffComment());
            copied.setEvidenceRatedBy(src.getEvidenceRatedBy());
            copied.setEvidenceRatedAt(src.getEvidenceRatedAt());
            copied = answerRepository.save(copied);

            for (Evidence evidence : src.getEvidences()) {
                copyEvidenceFork(evidence, copied);
            }
        }
    }

    /**
     * Staff upload evidence for a client's answer (consultant/manager/admin).
     * Allows upload even if assessment is already submitted (evidence can be added after submission).
     */
    @Transactional
    public List<EvidenceUploadResponse> uploadEvidencesForAnswerAsStaff(
            Long assessmentId,
            String staffEmail,
            String questionCode,
            int score,
            MultipartFile[] files
    ) {
        List<MultipartFile> uploadFiles = normalizeFiles(files);
        return uploadFiles.stream()
                .map(file -> uploadEvidenceForAnswerAsStaff(assessmentId, staffEmail, questionCode, score, file))
                .toList();
    }

    @Transactional
    public EvidenceUploadResponse uploadEvidenceForAnswerAsStaff(
            Long assessmentId,
            String staffEmail,
            String questionCode,
            int score,
            MultipartFile file
    ) {
        if (file == null || file.isEmpty()) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "File is required");
        }
        if (score < 0 || score > 5) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "Score must be between 0 and 5");
        }

        Assessment assessment = assessmentRepository.findById(assessmentId)
                .orElseThrow(() -> new ResponseStatusException(HttpStatus.NOT_FOUND, "Assessment not found"));

        AppUser staff = staffService.requireStaffByEmail(staffEmail);
        staffService.assertCanAccessAssessment(staff, assessment);

        QuestionnaireQuestion question = questionRepository.findByCode(questionCode)
                .orElseThrow(() -> new ResponseStatusException(HttpStatus.BAD_REQUEST, "Unknown questionCode: " + questionCode));

        AssessmentAnswer answer = answerRepository.findByAssessment_IdAndQuestion_Code(assessmentId, questionCode)
                .orElseGet(() -> {
                    AssessmentAnswer a = new AssessmentAnswer();
                    a.setAssessment(assessment);
                    a.setQuestion(question);
                    a.setScore(score);
                    return answerRepository.save(a);
                });
        answer.setScore(score);
        answer.setAnswered(true);
        answer.setAnsweredAt(Instant.now());
        answerRepository.save(answer);

        Evidence ev = new Evidence();
        ev.setAnswer(answer);
        ev.setUploadedBy(staff);
        ev.setOriginalFileName(safeFileName(file.getOriginalFilename()));
        ev.setContentType(normalizeContentType(file.getContentType()));
        ev.setSizeBytes(file.getSize());

        String evidenceKey = UUID.randomUUID().toString();
        String relative = evidenceKey + "/" + ev.getOriginalFileName();
        Path target = rootDir.resolve(relative).normalize();
        ensureUnderRoot(target);

        try {
            Files.createDirectories(target.getParent());
            try (InputStream in = file.getInputStream()) {
                Files.copy(in, target, StandardCopyOption.REPLACE_EXISTING);
            }
        } catch (Exception e) {
            throw new ResponseStatusException(HttpStatus.INTERNAL_SERVER_ERROR, "Failed to store file");
        }

        ev.setStoragePath(relative);
        Evidence saved = evidenceRepository.save(ev);

        return new EvidenceUploadResponse(
                saved.getId(),
                assessment.getId(),
                saved.getOriginalFileName(),
                saved.getContentType(),
                saved.getSizeBytes(),
                effectiveStaffRating(answer, saved),
                saved.getCreatedAt()
        );
    }

    /**
     * Deep-copies stored file and metadata for a new assessment answer (assessment versioning fork).
     */
    @Transactional
    public Evidence copyEvidenceFork(Evidence source, AssessmentAnswer newAnswer) {
        Evidence ev = new Evidence();
        ev.setAnswer(newAnswer);
        ev.setUploadedBy(source.getUploadedBy());
        ev.setOriginalFileName(source.getOriginalFileName());
        ev.setContentType(source.getContentType());
        ev.setSizeBytes(source.getSizeBytes());

        String evidenceKey = UUID.randomUUID().toString();
        String relative = evidenceKey + "/" + ev.getOriginalFileName();
        Path target = rootDir.resolve(relative).normalize();
        ensureUnderRoot(target);
        Path src = rootDir.resolve(source.getStoragePath()).normalize();
        ensureUnderRoot(src);

        try {
            Files.createDirectories(target.getParent());
            Files.copy(src, target, StandardCopyOption.REPLACE_EXISTING);
        } catch (Exception e) {
            throw new ResponseStatusException(HttpStatus.INTERNAL_SERVER_ERROR, "Failed to copy evidence file");
        }

        ev.setStoragePath(relative);
        return evidenceRepository.save(ev);
    }

    @Transactional(readOnly = true)
    public Evidence loadEvidenceForClient(Long evidenceId, String clientEmail) {
        Evidence ev = evidenceRepository.findById(evidenceId)
                .orElseThrow(() -> new ResponseStatusException(HttpStatus.NOT_FOUND, "Evidence not found"));
        String email = normalizeEmail(clientEmail);
        if (!ev.getAnswer().getAssessment().getClient().getEmail().equalsIgnoreCase(email)) {
            throw new ResponseStatusException(HttpStatus.FORBIDDEN, "Not allowed");
        }
        return ev;
    }

    @Transactional(readOnly = true)
    public Evidence loadEvidenceForStaff(Long evidenceId, String staffEmail) {
        Evidence ev = evidenceRepository.findById(evidenceId)
                .orElseThrow(() -> new ResponseStatusException(HttpStatus.NOT_FOUND, "Evidence not found"));
        AppUser staff = staffService.requireStaffByEmail(staffEmail);
        staffService.assertCanAccessAssessment(staff, ev.getAnswer().getAssessment());
        return ev;
    }

    @Transactional
    public void rateEvidence(Long evidenceId, String staffEmail, RateEvidenceRequest request) {
        Evidence ev = evidenceRepository.findById(evidenceId)
                .orElseThrow(() -> new ResponseStatusException(HttpStatus.NOT_FOUND, "Evidence not found"));
        AppUser staff = staffService.requireStaffByEmail(staffEmail);
        staffService.assertCanAccessAssessment(staff, ev.getAnswer().getAssessment());

        if (staff.getRole() == Role.CONSULTANT) {
            // Consultants can rate only their assigned clients (already enforced by assertCanAccessAssessment)
        }

        AssessmentAnswer answer = ev.getAnswer();
        answer.setEvidenceStaffRating(Objects.requireNonNull(request.rating(), "rating"));
        answer.setEvidenceStaffComment(request.comment());
        answer.setEvidenceRatedBy(staff);
        answer.setEvidenceRatedAt(Instant.now());
        answerRepository.save(answer);

        // Keep legacy columns in sync for older reports/screens that still inspect evidence rows directly.
        ev.setStaffRating(answer.getEvidenceStaffRating());
        ev.setStaffComment(answer.getEvidenceStaffComment());
        ev.setRatedBy(staff);
        ev.setRatedAt(answer.getEvidenceRatedAt());
        evidenceRepository.save(ev);
    }

    /**
     * Deletes one evidence (DB row + physical file when present).
     * Allowed for CLIENT (own assessment), CONSULTANT and MANAGER (authorized scope).
     * ADMIN is rejected.
     */
    @Transactional
    public void deleteEvidence(Long evidenceId, String actorEmail) {
        Evidence ev = evidenceRepository.findById(evidenceId)
                .orElseThrow(() -> new ResponseStatusException(HttpStatus.NOT_FOUND, "Evidence not found"));

        AppUser actor = committedAppUserLoader.findByEmailInNewTransaction(normalizeEmail(actorEmail))
                .orElseThrow(() -> new ResponseStatusException(HttpStatus.UNAUTHORIZED, "User not found"));

        AssessmentAnswer answer = ev.getAnswer();
        if (answer == null || answer.getAssessment() == null) {
            throw new ResponseStatusException(HttpStatus.NOT_FOUND, "Evidence not found");
        }
        Assessment assessment = answer.getAssessment();

        if (actor.getRole() == Role.CLIENT) {
            String clientEmail = assessment.getClient() != null ? assessment.getClient().getEmail() : null;
            if (clientEmail == null || !clientEmail.equalsIgnoreCase(actor.getEmail())) {
                throw new ResponseStatusException(HttpStatus.FORBIDDEN, "Not allowed");
            }
        } else if (actor.getRole() == Role.CONSULTANT || actor.getRole() == Role.MANAGER) {
            staffService.assertCanAccessAssessment(actor, assessment);
        } else {
            throw new ResponseStatusException(
                    HttpStatus.FORBIDDEN,
                    "Only clients, consultants and managers can delete evidences."
            );
        }

        String relativePath = ev.getStoragePath();
        // Detach from answer collection when loaded, then delete row.
        if (answer.getEvidences() != null) {
            answer.getEvidences().removeIf(e -> Objects.equals(e.getId(), ev.getId()));
        }
        evidenceRepository.delete(ev);
        evidenceRepository.flush();

        deleteStoredFileQuietly(relativePath);
    }

    private void deleteStoredFileQuietly(String storagePath) {
        if (storagePath == null || storagePath.isBlank()) {
            return;
        }
        try {
            Path file = resolveStoragePath(storagePath);
            Files.deleteIfExists(file);
            Path parent = file.getParent();
            if (parent != null && parent.startsWith(rootDir.toAbsolutePath().normalize())) {
                try (var stream = Files.list(parent)) {
                    if (stream.findAny().isEmpty()) {
                        Files.deleteIfExists(parent);
                    }
                }
            }
        } catch (ResponseStatusException ex) {
            // Invalid path under root — ignore physical cleanup; DB row already removed.
        } catch (Exception ignored) {
            // File already missing or not deletable — deletion of DB record remains valid.
        }
    }

    public Path resolveStoragePath(String storagePath) {
        Path p = rootDir.resolve(storagePath).normalize();
        ensureUnderRoot(p);
        return p;
    }

    private void ensureUnderRoot(Path p) {
        Path normalizedRoot = rootDir.toAbsolutePath().normalize();
        Path normalizedPath = p.toAbsolutePath().normalize();
        if (!normalizedPath.startsWith(normalizedRoot)) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "Invalid storage path");
        }
    }

    private static String normalizeEmail(String email) {
        return email == null ? "" : email.trim().toLowerCase(Locale.ROOT);
    }

    private static List<MultipartFile> normalizeFiles(MultipartFile[] files) {
        if (files == null || files.length == 0) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "File is required");
        }
        List<MultipartFile> uploadFiles = Arrays.stream(files)
                .filter(file -> file != null && !file.isEmpty())
                .toList();
        if (uploadFiles.isEmpty()) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "File is required");
        }
        return uploadFiles;
    }

    private static EvidenceRating effectiveStaffRating(AssessmentAnswer answer, Evidence evidence) {
        return answer.getEvidenceStaffRating() != null ? answer.getEvidenceStaffRating() : evidence.getStaffRating();
    }

    private static String safeFileName(String name) {
        if (name == null || name.isBlank()) return "evidence.bin";
        // Remove path separators
        String n = name.replace("\\\\", "_").replace("/", "_");
        if (n.length() > 255) n = n.substring(n.length() - 255);
        return n;
    }

    private static String normalizeContentType(String ct) {
        if (ct == null || ct.isBlank()) return "application/octet-stream";
        return ct;
    }
}

