package org.example.pfebackend.evidence;

import org.example.pfebackend.assessment.Assessment;
import org.example.pfebackend.assessment.AssessmentAnswer;
import org.example.pfebackend.assessment.QuestionnaireQuestion;
import org.example.pfebackend.project.Project;
import org.example.pfebackend.staff.StaffService;
import org.example.pfebackend.user.AppUser;
import org.example.pfebackend.user.CommittedAppUserLoader;
import org.example.pfebackend.user.Role;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.junit.jupiter.api.io.TempDir;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.http.HttpStatus;
import org.springframework.web.server.ResponseStatusException;

import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.Optional;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.doThrow;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

@ExtendWith(MockitoExtension.class)
class EvidenceDeleteServiceTest {

    @TempDir
    Path tempDir;

    @Mock
    private EvidenceRepository evidenceRepository;
    @Mock
    private org.example.pfebackend.assessment.AssessmentRepository assessmentRepository;
    @Mock
    private org.example.pfebackend.assessment.AssessmentAnswerRepository answerRepository;
    @Mock
    private org.example.pfebackend.assessment.QuestionnaireQuestionRepository questionRepository;
    @Mock
    private CommittedAppUserLoader committedAppUserLoader;
    @Mock
    private StaffService staffService;

    private EvidenceService service;

    @BeforeEach
    void setUp() {
        service = new EvidenceService(
                tempDir.toString(),
                evidenceRepository,
                assessmentRepository,
                answerRepository,
                questionRepository,
                committedAppUserLoader,
                staffService
        );
    }

    @Test
    void clientCanDeleteOwnEvidenceAndFile() throws Exception {
        AppUser client = user(Role.CLIENT, "client@test.local");
        Evidence evidence = sampleEvidence(client, "proof.pdf");
        Path stored = tempDir.resolve(evidence.getStoragePath());
        Files.createDirectories(stored.getParent());
        Files.writeString(stored, "pdf-bytes", java.nio.charset.StandardCharsets.UTF_8);

        when(evidenceRepository.findById(10L)).thenReturn(Optional.of(evidence));
        when(committedAppUserLoader.findByEmailInNewTransaction("client@test.local"))
                .thenReturn(Optional.of(client));

        service.deleteEvidence(10L, "client@test.local");

        verify(evidenceRepository).delete(evidence);
        assertThat(Files.exists(stored)).isFalse();
    }

    @Test
    void consultantOutsideScopeIsForbidden() {
        AppUser consultant = user(Role.CONSULTANT, "c@test.local");
        AppUser client = user(Role.CLIENT, "client@test.local");
        Evidence evidence = sampleEvidence(client, "proof.pdf");

        when(evidenceRepository.findById(10L)).thenReturn(Optional.of(evidence));
        when(committedAppUserLoader.findByEmailInNewTransaction("c@test.local"))
                .thenReturn(Optional.of(consultant));
        doThrow(new ResponseStatusException(HttpStatus.FORBIDDEN, "Not allowed"))
                .when(staffService)
                .assertCanAccessAssessment(eq(consultant), any(Assessment.class));

        assertThatThrownBy(() -> service.deleteEvidence(10L, "c@test.local"))
                .isInstanceOf(ResponseStatusException.class)
                .satisfies(ex -> assertThat(((ResponseStatusException) ex).getStatusCode()).isEqualTo(HttpStatus.FORBIDDEN));
        verify(evidenceRepository, never()).delete(any());
    }

    @Test
    void adminIsForbidden() {
        AppUser admin = user(Role.ADMIN, "admin@test.local");
        AppUser client = user(Role.CLIENT, "client@test.local");
        Evidence evidence = sampleEvidence(client, "proof.pdf");

        when(evidenceRepository.findById(10L)).thenReturn(Optional.of(evidence));
        when(committedAppUserLoader.findByEmailInNewTransaction("admin@test.local"))
                .thenReturn(Optional.of(admin));

        assertThatThrownBy(() -> service.deleteEvidence(10L, "admin@test.local"))
                .isInstanceOf(ResponseStatusException.class)
                .satisfies(ex -> assertThat(((ResponseStatusException) ex).getStatusCode()).isEqualTo(HttpStatus.FORBIDDEN));
    }

    @Test
    void missingEvidenceReturns404() {
        when(evidenceRepository.findById(99L)).thenReturn(Optional.empty());
        assertThatThrownBy(() -> service.deleteEvidence(99L, "client@test.local"))
                .isInstanceOf(ResponseStatusException.class)
                .satisfies(ex -> assertThat(((ResponseStatusException) ex).getStatusCode()).isEqualTo(HttpStatus.NOT_FOUND));
    }

    @Test
    void missingPhysicalFileStillDeletesDbRow() {
        AppUser client = user(Role.CLIENT, "client@test.local");
        Evidence evidence = sampleEvidence(client, "gone.pdf");
        when(evidenceRepository.findById(10L)).thenReturn(Optional.of(evidence));
        when(committedAppUserLoader.findByEmailInNewTransaction("client@test.local"))
                .thenReturn(Optional.of(client));

        service.deleteEvidence(10L, "client@test.local");
        verify(evidenceRepository).delete(evidence);
    }

    private static AppUser user(Role role, String email) {
        AppUser u = new AppUser();
        u.setFullName(role.name());
        u.setEmail(email);
        u.setPassword("x");
        u.setRole(role);
        return u;
    }

    private static Evidence sampleEvidence(AppUser client, String fileName) {
        Project project = new Project();
        project.setName("P");
        project.setClient(client);

        Assessment assessment = new Assessment();
        assessment.setClient(client);
        assessment.setProject(project);
        assessment.setYear(2026);
        assessment.setVersion(1);

        QuestionnaireQuestion question = new QuestionnaireQuestion();
        question.setCode("ndi_dg_01");
        question.setText("Q");
        question.setSortOrder(1);

        AssessmentAnswer answer = new AssessmentAnswer();
        answer.setAssessment(assessment);
        answer.setQuestion(question);
        answer.setScore(2);
        answer.setAnswered(true);
        answer.setEvidences(new ArrayList<>());

        Evidence evidence = new Evidence();
        try {
            var idField = Evidence.class.getDeclaredField("id");
            idField.setAccessible(true);
            idField.set(evidence, 10L);
        } catch (Exception ignored) {
            // id may stay null in unit test; repository uses the same instance
        }
        evidence.setAnswer(answer);
        evidence.setUploadedBy(client);
        evidence.setOriginalFileName(fileName);
        evidence.setContentType("application/pdf");
        evidence.setSizeBytes(9);
        evidence.setStoragePath("abc/" + fileName);
        answer.getEvidences().add(evidence);
        return evidence;
    }
}
