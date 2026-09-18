package org.example.pfebackend.assessment;

import org.example.pfebackend.assessment.dto.AssessmentResponse;
import org.example.pfebackend.assessment.dto.GenerateReportRequestDto;
import org.example.pfebackend.assessment.dto.RecommendationTargetRequest;
import org.example.pfebackend.user.AppUser;
import org.example.pfebackend.user.Role;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.web.server.ResponseStatusException;

import java.util.List;
import java.util.Optional;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.doNothing;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

@ExtendWith(MockitoExtension.class)
class RecommendationServiceTest {

    @Mock
    private AssessmentRepository assessmentRepository;
    @Mock
    private AssessmentService assessmentService;
    @Mock
    private org.example.pfebackend.staff.StaffService staffService;
    @Mock
    private AiRecommendationClient aiRecommendationClient;

    private RecommendationService recommendationService;

    @BeforeEach
    void setUp() {
        recommendationService = new RecommendationService(
                assessmentRepository,
                assessmentService,
                staffService,
                aiRecommendationClient,
                "jdbc:postgresql://postgres:5432/pfe_backend_db"
        );
    }

    @Test
    void rejectsAdminRole() {
        AppUser admin = user(Role.ADMIN);

        assertThatThrownBy(() -> recommendationService.setRecommendationTarget(
                admin, 1L, new RecommendationTargetRequest(3.5)
        )).isInstanceOf(ResponseStatusException.class)
                .hasMessageContaining("403");
    }

    @Test
    void rejectsClientRole() {
        AppUser client = user(Role.CLIENT);

        assertThatThrownBy(() -> recommendationService.setRecommendationTarget(
                client, 1L, new RecommendationTargetRequest(3.5)
        )).isInstanceOf(ResponseStatusException.class)
                .hasMessageContaining("403");
    }

    @Test
    void rejectsDraftAssessment() {
        AppUser consultant = user(Role.CONSULTANT);
        Assessment assessment = submittedAssessment();
        assessment.setStatus(AssessmentStatus.DRAFT);
        when(assessmentRepository.findById(1L)).thenReturn(Optional.of(assessment));
        doNothing().when(staffService).assertCanAccessAssessment(consultant, assessment);
        when(assessmentRepository.findFirstByClient_IdAndStatusOrderByYearDescVersionDesc(
                eq(10L), eq(AssessmentStatus.SUBMITTED)
        )).thenReturn(Optional.empty());

        assertThatThrownBy(() -> recommendationService.setRecommendationTarget(
                consultant, 1L, new RecommendationTargetRequest(3.5)
        )).isInstanceOf(ResponseStatusException.class)
                .hasMessageContaining("soumise");
    }

    @Test
    void rejectsTargetLessOrEqualToCurrentScore() {
        AppUser consultant = user(Role.CONSULTANT);
        Assessment assessment = submittedAssessment();
        when(assessmentRepository.findById(1L)).thenReturn(Optional.of(assessment));
        doNothing().when(staffService).assertCanAccessAssessment(consultant, assessment);
        when(assessmentRepository.findFirstByClient_IdAndStatusOrderByYearDescVersionDesc(
                eq(10L), eq(AssessmentStatus.SUBMITTED)
        )).thenReturn(Optional.of(assessment));
        when(assessmentService.renderAssessment(assessment)).thenReturn(ndiResponse(2.4, null));

        assertThatThrownBy(() -> recommendationService.setRecommendationTarget(
                consultant, 1L, new RecommendationTargetRequest(2.4)
        )).isInstanceOf(ResponseStatusException.class)
                .hasMessageContaining("strictement supérieure");
    }

    @Test
    void rejectsMissingTargetWhenGeneratingReport() {
        AppUser manager = user(Role.MANAGER);
        Assessment assessment = submittedAssessment();
        assessment.setRecommendationTargetScore(null);
        when(assessmentRepository.findById(1L)).thenReturn(Optional.of(assessment));
        doNothing().when(staffService).assertCanAccessAssessment(manager, assessment);
        when(assessmentRepository.findFirstByClient_IdAndStatusOrderByYearDescVersionDesc(
                eq(10L), eq(AssessmentStatus.SUBMITTED)
        )).thenReturn(Optional.of(assessment));
        when(assessmentService.renderAssessment(assessment)).thenReturn(ndiResponse(2.4, null));

        assertThatThrownBy(() -> recommendationService.generateRecommendationReport(manager, 1L))
                .isInstanceOf(ResponseStatusException.class)
                .hasMessageContaining("cible");
        verify(aiRecommendationClient, never()).generateReportPdf(any(GenerateReportRequestDto.class));
    }

    @Test
    void savesValidTarget() {
        AppUser consultant = user(Role.CONSULTANT);
        Assessment assessment = submittedAssessment();
        when(assessmentRepository.findById(1L)).thenReturn(Optional.of(assessment));
        doNothing().when(staffService).assertCanAccessAssessment(consultant, assessment);
        when(assessmentRepository.findFirstByClient_IdAndStatusOrderByYearDescVersionDesc(
                eq(10L), eq(AssessmentStatus.SUBMITTED)
        )).thenReturn(Optional.of(assessment));
        when(assessmentService.renderAssessment(assessment)).thenReturn(ndiResponse(2.4, null));
        when(assessmentRepository.save(assessment)).thenReturn(assessment);

        var response = recommendationService.setRecommendationTarget(
                consultant, 1L, new RecommendationTargetRequest(3.5)
        );

        assertThat(response.recommendationTargetScore()).isEqualTo(3.5);
        assertThat(assessment.getRecommendationTargetScore()).isEqualTo(3.5);
        verify(assessmentRepository).save(assessment);
    }

    @Test
    void resolvesDraftRequestToLatestSubmittedForTarget() {
        AppUser consultant = user(Role.CONSULTANT);
        Assessment draft = submittedAssessment();
        draft.setStatus(AssessmentStatus.DRAFT);
        draft.setVersion(19);
        Assessment submitted = submittedAssessment();
        submitted.setVersion(18);
        when(assessmentRepository.findById(1L)).thenReturn(Optional.of(draft));
        doNothing().when(staffService).assertCanAccessAssessment(consultant, draft);
        when(assessmentRepository.findFirstByClient_IdAndStatusOrderByYearDescVersionDesc(
                eq(10L), eq(AssessmentStatus.SUBMITTED)
        )).thenReturn(Optional.of(submitted));
        when(assessmentService.renderAssessment(submitted)).thenReturn(ndiResponse(1.83, null));
        when(assessmentRepository.save(submitted)).thenReturn(submitted);

        var response = recommendationService.setRecommendationTarget(
                consultant, 1L, new RecommendationTargetRequest(3.5)
        );

        assertThat(response.assessmentId()).isEqualTo(1L);
        assertThat(response.recommendationTargetScore()).isEqualTo(3.5);
        assertThat(submitted.getRecommendationTargetScore()).isEqualTo(3.5);
        verify(assessmentRepository).save(submitted);
    }

    private static AppUser user(Role role) {
        AppUser user = new AppUser();
        user.setRole(role);
        user.setEmail(role.name().toLowerCase() + "@test.local");
        user.setFullName(role.name());
        return user;
    }

    private static Assessment submittedAssessment() {
        AppUser client = user(Role.CLIENT);
        try {
            var idField = AppUser.class.getDeclaredField("id");
            idField.setAccessible(true);
            idField.set(client, 10L);
        } catch (ReflectiveOperationException e) {
            throw new IllegalStateException(e);
        }
        Assessment assessment = new Assessment();
        try {
            var idField = Assessment.class.getDeclaredField("id");
            idField.setAccessible(true);
            idField.set(assessment, 1L);
        } catch (ReflectiveOperationException e) {
            throw new IllegalStateException(e);
        }
        assessment.setClient(client);
        assessment.setYear(2026);
        assessment.setVersion(2);
        assessment.setStatus(AssessmentStatus.SUBMITTED);
        return assessment;
    }

    private static AssessmentResponse ndiResponse(double score, Double target) {
        return new AssessmentResponse(
                1L,
                2026,
                2,
                2,
                "SUBMITTED",
                "SUBMITTED",
                10L,
                "Client",
                "client@test.local",
                null,
                null,
                null,
                null,
                null,
                null,
                null,
                target,
                score,
                score,
                "Managed",
                1,
                1,
                true,
                false,
                100,
                "SUBMITTED",
                List.of(new AssessmentResponse.FrameworkStatusDto(
                        "NDI", "SUBMITTED", score, score, 1, 1, true, null, null
                )),
                List.of(new AssessmentResponse.SegmentScoreDto(
                        "ndi_dg",
                        "ndi_dg",
                        "Data Governance",
                        2,
                        2.0,
                        "Managed",
                        1,
                        1,
                        true,
                        11.75,
                        List.of(new AssessmentResponse.QuestionAnswerDto(
                                1L,
                                "ndi_dg_01",
                                "Q1",
                                2,
                                "Managed",
                                null,
                                null,
                                null,
                                null,
                                null,
                                null,
                                null,
                                List.of(),
                                true
                        ))
                ))
        );
    }
}
