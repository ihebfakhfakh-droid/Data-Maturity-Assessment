package org.example.pfebackend.evidence;

import org.example.pfebackend.assessment.Assessment;
import org.example.pfebackend.assessment.AssessmentAnswer;
import org.example.pfebackend.assessment.QuestionnaireQuestion;
import org.example.pfebackend.project.Project;
import org.example.pfebackend.staff.StaffService;
import org.example.pfebackend.user.AppUser;
import org.example.pfebackend.user.Role;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.http.HttpStatus;
import org.springframework.web.server.ResponseStatusException;

import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.Optional;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.doThrow;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

@ExtendWith(MockitoExtension.class)
class AcceptanceCriteriaReportServiceTest {

    @Mock
    private EvidenceRepository evidenceRepository;
    @Mock
    private EvidenceService evidenceService;
    @Mock
    private StaffService staffService;
    @Mock
    private AiAcceptanceCriteriaClient aiAcceptanceCriteriaClient;

    private AcceptanceCriteriaReportService service;
    private Path tempFile;

    @BeforeEach
    void setUp() throws Exception {
        service = new AcceptanceCriteriaReportService(
                evidenceRepository,
                evidenceService,
                staffService,
                aiAcceptanceCriteriaClient
        );
        tempFile = Files.createTempFile("evidence-ac-", ".png");
        Files.write(tempFile, "png-bytes".getBytes(StandardCharsets.UTF_8));
        tempFile.toFile().deleteOnExit();
    }

    @Test
    void refusesAdmin() {
        AppUser admin = user(Role.ADMIN);

        assertThatThrownBy(() -> service.generateReport(admin, 1L))
                .isInstanceOf(ResponseStatusException.class)
                .satisfies(ex -> assertThat(((ResponseStatusException) ex).getStatusCode()).isEqualTo(HttpStatus.FORBIDDEN));
    }

    @Test
    void refusesWhenEvidenceMissing() {
        AppUser consultant = user(Role.CONSULTANT);
        when(evidenceRepository.findById(99L)).thenReturn(Optional.empty());

        assertThatThrownBy(() -> service.generateReport(consultant, 99L))
                .isInstanceOf(ResponseStatusException.class)
                .satisfies(ex -> assertThat(((ResponseStatusException) ex).getStatusCode()).isEqualTo(HttpStatus.NOT_FOUND));
    }

    @Test
    void refusesUnaffectedConsultant() {
        AppUser consultant = user(Role.CONSULTANT);
        Evidence evidence = sampleEvidence();
        when(evidenceRepository.findById(1L)).thenReturn(Optional.of(evidence));
        doThrow(new ResponseStatusException(HttpStatus.FORBIDDEN, "Not allowed"))
                .when(staffService)
                .assertCanAccessAssessment(eq(consultant), any(Assessment.class));

        assertThatThrownBy(() -> service.generateReport(consultant, 1L))
                .isInstanceOf(ResponseStatusException.class)
                .satisfies(ex -> assertThat(((ResponseStatusException) ex).getStatusCode()).isEqualTo(HttpStatus.FORBIDDEN));
    }

    @Test
    void allowsAssignedConsultantAndReturnsPdf() {
        AppUser consultant = user(Role.CONSULTANT);
        Evidence evidence = sampleEvidence();
        when(evidenceRepository.findById(1L)).thenReturn(Optional.of(evidence));
        when(evidenceService.resolveStoragePath(evidence.getStoragePath())).thenReturn(tempFile);
        byte[] pdf = "%PDF-1.4 ok".getBytes(StandardCharsets.UTF_8);
        when(aiAcceptanceCriteriaClient.generateReportPdf(any())).thenReturn(pdf);

        AcceptanceCriteriaReportService.AcceptanceCriteriaReportResult result =
                service.generateReport(consultant, 1L);

        assertThat(result.pdfBytes()).startsWith("%PDF".getBytes(StandardCharsets.UTF_8));
        assertThat(result.filename()).endsWith(".pdf");
        verify(staffService).assertCanAccessAssessment(eq(consultant), any(Assessment.class));
        verify(aiAcceptanceCriteriaClient).generateReportPdf(any());
    }

    @Test
    void allowsManager() {
        AppUser manager = user(Role.MANAGER);
        Evidence evidence = sampleEvidence();
        when(evidenceRepository.findById(1L)).thenReturn(Optional.of(evidence));
        when(evidenceService.resolveStoragePath(evidence.getStoragePath())).thenReturn(tempFile);
        when(aiAcceptanceCriteriaClient.generateReportPdf(any()))
                .thenReturn("%PDF-1.4 manager".getBytes(StandardCharsets.UTF_8));

        AcceptanceCriteriaReportService.AcceptanceCriteriaReportResult result =
                service.generateReport(manager, 1L);
        assertThat(result.pdfBytes()).isNotEmpty();
    }

    @Test
    void missingPhysicalFileReturns404() {
        AppUser consultant = user(Role.CONSULTANT);
        Evidence evidence = sampleEvidence();
        when(evidenceRepository.findById(1L)).thenReturn(Optional.of(evidence));
        when(evidenceService.resolveStoragePath(evidence.getStoragePath()))
                .thenReturn(Path.of("C:/does/not/exist/evidence.bin"));

        assertThatThrownBy(() -> service.generateReport(consultant, 1L))
                .isInstanceOf(ResponseStatusException.class)
                .satisfies(ex -> assertThat(((ResponseStatusException) ex).getStatusCode()).isEqualTo(HttpStatus.NOT_FOUND));
    }

    private static AppUser user(Role role) {
        AppUser u = new AppUser();
        u.setFullName(role.name() + " User");
        u.setEmail(role.name().toLowerCase() + "@test.local");
        u.setPassword("x");
        u.setRole(role);
        return u;
    }

    private static Evidence sampleEvidence() {
        AppUser client = user(Role.CLIENT);
        client.setFullName("Client Demo");
        client.setEmail("client@example.com");

        Project project = new Project();
        project.setName("Projet Alpha");
        project.setClient(client);

        Assessment assessment = new Assessment();
        assessment.setClient(client);
        assessment.setProject(project);
        assessment.setYear(2026);
        assessment.setVersion(2);

        QuestionnaireQuestion question = new QuestionnaireQuestion();
        question.setCode("ndi_dg_01");
        question.setText("Has the entity established a strategy?");
        question.setSortOrder(1);

        AssessmentAnswer answer = new AssessmentAnswer();
        answer.setAssessment(assessment);
        answer.setQuestion(question);
        answer.setScore(1);
        answer.setAnswered(true);

        Evidence evidence = new Evidence();
        evidence.setAnswer(answer);
        evidence.setUploadedBy(client);
        evidence.setOriginalFileName("proof.png");
        evidence.setContentType("image/png");
        evidence.setSizeBytes(10);
        evidence.setStoragePath("abc/proof.png");
        return evidence;
    }
}
