package org.example.pfebackend.assessment.api;

import jakarta.validation.Valid;
import org.example.pfebackend.assessment.Assessment;
import org.example.pfebackend.assessment.AssessmentRepository;
import org.example.pfebackend.assessment.AssessmentService;
import org.example.pfebackend.assessment.QuestionnaireService;
import org.example.pfebackend.assessment.dto.AssessmentResponse;
import org.example.pfebackend.assessment.dto.AssessmentVersionDiffDto;
import org.example.pfebackend.assessment.dto.AssessmentVersionSummaryDto;
import org.example.pfebackend.assessment.dto.QuestionnaireResponse;
import org.example.pfebackend.assessment.dto.SubmitAnswersRequest;
import org.example.pfebackend.project.ClientEntitlementService;
import org.example.pfebackend.project.ClientProjectEntitlements;
import org.example.pfebackend.staff.StaffService;
import org.example.pfebackend.user.AppUser;
import org.example.pfebackend.user.AppUserRepository;
import org.springframework.http.HttpStatus;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.security.oauth2.jwt.Jwt;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestMethod;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.server.ResponseStatusException;

import java.util.List;
import java.util.Map;

@RestController
@RequestMapping("/api/admin/assessments")
public class AdminAssessmentController {

    private final AppUserRepository userRepository;
    private final AssessmentRepository assessmentRepository;
    private final AssessmentService assessmentService;
    private final QuestionnaireService questionnaireService;
    private final ClientEntitlementService entitlementService;
    private final StaffService staffService;

    public AdminAssessmentController(
            AppUserRepository userRepository,
            AssessmentRepository assessmentRepository,
            AssessmentService assessmentService,
            QuestionnaireService questionnaireService,
            ClientEntitlementService entitlementService,
            StaffService staffService
    ) {
        this.userRepository = userRepository;
        this.assessmentRepository = assessmentRepository;
        this.assessmentService = assessmentService;
        this.questionnaireService = questionnaireService;
        this.entitlementService = entitlementService;
        this.staffService = staffService;
    }

    /** Clients with at least one submitted assessment. Admin and manager: all; consultant: only assigned clients. */
    @GetMapping("/clients")
    public List<Map<String, Object>> clients(@AuthenticationPrincipal Jwt jwt) {
        AppUser staff = staffService.requireStaffByEmail(jwt.getSubject());
        return staffService.listClientsWithSubmittedAssessments(staff);
    }

    @GetMapping("/clients/{clientId}")
    public List<Map<String, Object>> assessmentsByClient(
            @AuthenticationPrincipal Jwt jwt,
            @PathVariable Long clientId
    ) {
        AppUser staff = staffService.requireStaffByEmail(jwt.getSubject());
        AppUser client = userRepository.findById(clientId)
                .orElseThrow(() -> new ResponseStatusException(HttpStatus.NOT_FOUND, "Client not found"));
        staffService.assertCanAccessClientData(staff, client);

        return assessmentService.listMainAssessmentSummariesForClient(client);
    }

    @GetMapping("/clients/{clientId}/years/{year}/versions")
    public List<AssessmentVersionSummaryDto> listAssessmentVersionsForYear(
            @AuthenticationPrincipal Jwt jwt,
            @PathVariable Long clientId,
            @PathVariable int year
    ) {
        AppUser staff = staffService.requireStaffByEmail(jwt.getSubject());
        AppUser client = userRepository.findById(clientId)
                .orElseThrow(() -> new ResponseStatusException(HttpStatus.NOT_FOUND, "Client not found"));
        staffService.assertCanViewAssessmentVersions(staff, client);
        return assessmentService.listVersionSummariesForClientYear(clientId, year);
    }

    @GetMapping("/{assessmentId}/diff-from-previous")
    public AssessmentVersionDiffDto diffFromPrevious(
            @AuthenticationPrincipal Jwt jwt,
            @PathVariable Long assessmentId
    ) {
        AppUser staff = staffService.requireStaffByEmail(jwt.getSubject());
        Assessment assessment = assessmentRepository.findById(assessmentId)
                .orElseThrow(() -> new ResponseStatusException(HttpStatus.NOT_FOUND, "Assessment not found"));
        staffService.assertCanAccessAssessment(staff, assessment);
        return assessmentService.diffFromPreviousVersion(assessmentId);
    }

    @GetMapping("/{assessmentId}")
    public AssessmentResponse getAssessment(
            @AuthenticationPrincipal Jwt jwt,
            @PathVariable Long assessmentId
    ) {
        AppUser staff = staffService.requireStaffByEmail(jwt.getSubject());
        Assessment assessment = assessmentRepository.findById(assessmentId)
                .orElseThrow(() -> new ResponseStatusException(HttpStatus.NOT_FOUND, "Assessment not found"));
        staffService.assertCanAccessAssessment(staff, assessment);
        return assessmentService.renderAssessment(assessment);
    }

    @GetMapping("/{assessmentId}/questionnaire")
    public QuestionnaireResponse questionnaire(
            @AuthenticationPrincipal Jwt jwt,
            @PathVariable Long assessmentId
    ) {
        AppUser staff = staffService.requireStaffByEmail(jwt.getSubject());
        Assessment assessment = assessmentRepository.findById(assessmentId)
                .orElseThrow(() -> new ResponseStatusException(HttpStatus.NOT_FOUND, "Assessment not found"));
        staffService.assertCanEditAssessment(staff, assessment);

        ClientProjectEntitlements entitlements = assessment.getProject() != null
                ? entitlementService.entitlementsForProject(assessment.getProject().getId())
                : entitlementService.entitlementsForClientEmail(assessment.getClient().getEmail());
        return questionnaireService.getQuestionnaire(entitlements);
    }

    @RequestMapping(
            value = {
                    "/{assessmentId}/answers",
                    "/{assessmentId}/draft",
                    "/{assessmentId}/save"
            },
            method = {RequestMethod.POST, RequestMethod.PUT, RequestMethod.PATCH}
    )
    public AssessmentResponse saveDraftAnswers(
            @AuthenticationPrincipal Jwt jwt,
            @PathVariable Long assessmentId,
            @RequestBody @Valid SubmitAnswersRequest request
    ) {
        AppUser staff = staffService.requireStaffByEmail(jwt.getSubject());
        Assessment assessment = assessmentRepository.findById(assessmentId)
                .orElseThrow(() -> new ResponseStatusException(HttpStatus.NOT_FOUND, "Assessment not found"));
        staffService.assertCanEditAssessment(staff, assessment);

        return assessmentService.saveDraftAnswers(assessmentId, assessment.getClient().getEmail(), request);
    }

    @RequestMapping(value = "/{assessmentId}/submit", method = RequestMethod.POST)
    public AssessmentResponse submitAsStaff(
            @AuthenticationPrincipal Jwt jwt,
            @PathVariable Long assessmentId,
            @RequestBody @Valid SubmitAnswersRequest request
    ) {
        AppUser staff = staffService.requireStaffByEmail(jwt.getSubject());
        Assessment assessment = assessmentRepository.findById(assessmentId)
                .orElseThrow(() -> new ResponseStatusException(HttpStatus.NOT_FOUND, "Assessment not found"));
        staffService.assertCanEditAssessment(staff, assessment);

        return assessmentService.submitAnswersAsStaff(assessmentId, staff, request);
    }

    @RequestMapping(
            value = "/{assessmentId}/answers/{questionCode}",
            method = {RequestMethod.POST, RequestMethod.PUT, RequestMethod.PATCH}
    )
    public AssessmentResponse saveDraftAnswer(
            @AuthenticationPrincipal Jwt jwt,
            @PathVariable Long assessmentId,
            @PathVariable String questionCode,
            @RequestBody @Valid SubmitAnswersRequest.AnswerItem request
    ) {
        AppUser staff = staffService.requireStaffByEmail(jwt.getSubject());
        Assessment assessment = assessmentRepository.findById(assessmentId)
                .orElseThrow(() -> new ResponseStatusException(HttpStatus.NOT_FOUND, "Assessment not found"));
        staffService.assertCanEditAssessment(staff, assessment);

        SubmitAnswersRequest.AnswerItem answer = new SubmitAnswersRequest.AnswerItem(
                questionCode,
                request.score(),
                request.answered(),
                request.comment()
        );
        return assessmentService.saveDraftAnswers(
                assessmentId,
                assessment.getClient().getEmail(),
                new SubmitAnswersRequest(List.of(answer), null, null)
        );
    }
}
