package org.example.pfebackend.evidence;

import org.example.pfebackend.assessment.Assessment;
import org.example.pfebackend.assessment.AssessmentAnswer;
import org.example.pfebackend.assessment.QuestionnaireDomain;
import org.example.pfebackend.assessment.QuestionnaireQuestion;
import org.example.pfebackend.assessment.QuestionnaireSegment;
import org.example.pfebackend.project.Project;
import org.example.pfebackend.staff.StaffService;
import org.example.pfebackend.user.AppUser;
import org.example.pfebackend.user.Role;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.web.server.ResponseStatusException;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;
import java.util.Locale;
import java.util.Objects;
import java.util.regex.Pattern;

@Service
public class AcceptanceCriteriaReportService {

    private static final DateTimeFormatter GENERATION_DATE_FORMAT =
            DateTimeFormatter.ofPattern("dd/MM/yyyy HH:mm");
    private static final Pattern UNSAFE_FILENAME = Pattern.compile("[\\\\/:*?\"<>|\\r\\n]+");

    private final EvidenceRepository evidenceRepository;
    private final EvidenceService evidenceService;
    private final StaffService staffService;
    private final AiAcceptanceCriteriaClient aiAcceptanceCriteriaClient;

    public AcceptanceCriteriaReportService(
            EvidenceRepository evidenceRepository,
            EvidenceService evidenceService,
            StaffService staffService,
            AiAcceptanceCriteriaClient aiAcceptanceCriteriaClient
    ) {
        this.evidenceRepository = evidenceRepository;
        this.evidenceService = evidenceService;
        this.staffService = staffService;
        this.aiAcceptanceCriteriaClient = aiAcceptanceCriteriaClient;
    }

    @Transactional(readOnly = true)
    public AcceptanceCriteriaReportResult generateReport(AppUser staff, Long evidenceId) {
        requireConsultantOrManager(staff);

        Evidence evidence = evidenceRepository.findById(evidenceId)
                .orElseThrow(() -> new ResponseStatusException(HttpStatus.NOT_FOUND, "Evidence inexistante."));

        AssessmentAnswer answer = evidence.getAnswer();
        if (answer == null) {
            throw new ResponseStatusException(HttpStatus.NOT_FOUND, "AssessmentAnswer introuvable pour cette evidence.");
        }

        Assessment assessment = answer.getAssessment();
        if (assessment == null) {
            throw new ResponseStatusException(HttpStatus.NOT_FOUND, "Assessment introuvable pour cette evidence.");
        }

        staffService.assertCanAccessAssessment(staff, assessment);

        QuestionnaireQuestion question = answer.getQuestion();
        if (question == null) {
            throw new ResponseStatusException(HttpStatus.NOT_FOUND, "Question introuvable pour cette evidence.");
        }

        Path storagePath = evidenceService.resolveStoragePath(evidence.getStoragePath());
        if (!Files.exists(storagePath) || !Files.isRegularFile(storagePath)) {
            throw new ResponseStatusException(HttpStatus.NOT_FOUND, "Fichier physique introuvable pour cette evidence.");
        }

        byte[] fileBytes;
        try {
            fileBytes = Files.readAllBytes(storagePath);
        } catch (IOException ex) {
            throw new ResponseStatusException(
                    HttpStatus.INTERNAL_SERVER_ERROR,
                    "Impossible de lire le fichier d'évidence."
            );
        }
        if (fileBytes.length == 0) {
            throw new ResponseStatusException(HttpStatus.UNPROCESSABLE_ENTITY, "Le fichier d'évidence est vide.");
        }

        DomainInfo domainInfo = resolveDomainInfo(question);
        String maturityLevel = maturityLabelForScore(answer.getScore(), question);
        String framework = resolveFramework(question);

        AppUser client = assessment.getClient();
        Project project = assessment.getProject();
        String clientFullName = client != null ? blankToNull(client.getFullName()) : null;
        String clientEmail = client != null ? blankToNull(client.getEmail()) : null;
        String projectName = project != null ? blankToNull(project.getName()) : null;
        String generationDate = LocalDateTime.now().format(GENERATION_DATE_FORMAT);

        AiAcceptanceCriteriaClient.AcceptanceCriteriaReportRequest request =
                new AiAcceptanceCriteriaClient.AcceptanceCriteriaReportRequest(
                        fileBytes,
                        evidence.getOriginalFileName(),
                        evidence.getContentType(),
                        framework,
                        domainInfo.domainName(),
                        domainInfo.domainCode(),
                        question.getText(),
                        question.getCode(),
                        answer.getScore(),
                        maturityLevel,
                        clientFullName,
                        clientEmail,
                        projectName,
                        assessment.getVersion(),
                        generationDate
                );

        byte[] pdf = aiAcceptanceCriteriaClient.generateReportPdf(request);
        String filename = buildReportFilename(clientFullName, projectName, evidence.getOriginalFileName());
        return new AcceptanceCriteriaReportResult(pdf, filename);
    }

    private static void requireConsultantOrManager(AppUser staff) {
        if (staff == null) {
            throw new ResponseStatusException(HttpStatus.UNAUTHORIZED, "Utilisateur non authentifié.");
        }
        if (staff.getRole() != Role.CONSULTANT && staff.getRole() != Role.MANAGER) {
            throw new ResponseStatusException(
                    HttpStatus.FORBIDDEN,
                    "Seuls les consultants et managers peuvent générer le rapport Acceptance Criteria."
            );
        }
    }

    private static DomainInfo resolveDomainInfo(QuestionnaireQuestion question) {
        QuestionnaireDomain domain = question.getDomain();
        QuestionnaireSegment segment = question.getSegment();

        String domainName = null;
        String domainCode = null;

        if (domain != null) {
            domainName = blankToNull(domain.getTitle());
            domainCode = blankToNull(domain.getCode());
        }
        if (domainName == null && segment != null) {
            domainName = blankToNull(segment.getTitle());
        }
        if (domainCode == null && segment != null && segment.getCode() != null) {
            String seg = segment.getCode().trim().toLowerCase(Locale.ROOT);
            if (seg.startsWith("ndi_")) {
                domainCode = seg.substring(4).toUpperCase(Locale.ROOT);
            } else {
                domainCode = segment.getCode();
            }
        }
        if (domainCode == null && question.getCode() != null) {
            String qc = question.getCode().trim().toLowerCase(Locale.ROOT);
            if (qc.startsWith("ndi_")) {
                String[] parts = qc.split("_");
                if (parts.length >= 2) {
                    domainCode = parts[1].toUpperCase(Locale.ROOT);
                }
            }
        }
        return new DomainInfo(domainName, domainCode);
    }

    private static String resolveFramework(QuestionnaireQuestion question) {
        String code = question.getCode() == null ? "" : question.getCode().toLowerCase(Locale.ROOT);
        if (code.startsWith("ndi_")) {
            return "NDI";
        }
        if (code.startsWith("cmmi_")) {
            return "CMMI";
        }
        QuestionnaireSegment segment = question.getSegment();
        if (segment != null && segment.getMaturityFramework() != null
                && segment.getMaturityFramework().getCode() != null) {
            return segment.getMaturityFramework().getCode();
        }
        return "NDI";
    }

    private static String maturityLabelForScore(int score, QuestionnaireQuestion question) {
        String code = question.getCode() == null ? "" : question.getCode().toLowerCase(Locale.ROOT);
        int s = Math.min(5, Math.max(0, score));
        if (code.startsWith("ndi_") || code.isBlank()) {
            return switch (s) {
                case 0 -> "Level 0: Absence of Capabilities";
                case 1 -> "Level 1: Establishing";
                case 2 -> "Level 2: Defined";
                case 3 -> "Level 3: Activated";
                case 4 -> "Level 4: Managed";
                case 5 -> "Level 5: Pioneer";
                default -> "Level " + s;
            };
        }
        return "Level " + s;
    }

    static String buildReportFilename(String clientName, String projectName, String evidenceName) {
        String client = slug(clientName, "client");
        String project = slug(projectName, "projet");
        String evidence = slug(stripExtension(evidenceName), "evidence");
        return "acceptance-criteria-" + client + "-" + project + "-" + evidence + ".pdf";
    }

    private static String stripExtension(String name) {
        if (name == null || name.isBlank()) {
            return "evidence";
        }
        int dot = name.lastIndexOf('.');
        return dot > 0 ? name.substring(0, dot) : name;
    }

    private static String slug(String value, String fallback) {
        String raw = value == null || value.isBlank() ? fallback : value.trim().toLowerCase(Locale.ROOT);
        raw = UNSAFE_FILENAME.matcher(raw).replaceAll("-");
        raw = raw.replaceAll("[^a-z0-9._-]+", "-");
        raw = raw.replaceAll("-{2,}", "-");
        raw = raw.replaceAll("^[._-]+|[._-]+$", "");
        if (raw.isBlank()) {
            raw = fallback;
        }
        return raw.length() > 60 ? raw.substring(0, 60) : raw;
    }

    private static String blankToNull(String value) {
        if (value == null) {
            return null;
        }
        String trimmed = value.trim();
        return trimmed.isEmpty() ? null : trimmed;
    }

    private record DomainInfo(String domainName, String domainCode) {
    }

    public record AcceptanceCriteriaReportResult(byte[] pdfBytes, String filename) {
        public AcceptanceCriteriaReportResult {
            Objects.requireNonNull(pdfBytes, "pdfBytes");
            Objects.requireNonNull(filename, "filename");
        }
    }
}
