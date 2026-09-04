package org.example.pfebackend.assessment.api;

import jakarta.validation.Valid;
import org.example.pfebackend.assessment.Assessment;
import org.example.pfebackend.assessment.AssessmentService;
import org.example.pfebackend.assessment.QuestionnaireService;
import org.example.pfebackend.assessment.dto.AssessmentResponse;
import org.example.pfebackend.assessment.dto.AssessmentVersionSummaryDto;
import org.example.pfebackend.assessment.dto.CreateAssessmentRequest;
import org.example.pfebackend.assessment.dto.QuestionnaireResponse;
import org.example.pfebackend.assessment.dto.SubmitAnswersRequest;
import org.example.pfebackend.project.ClientEntitlementService;
import org.example.pfebackend.project.ClientProjectEntitlements;
import org.example.pfebackend.project.Framework;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.security.oauth2.jwt.Jwt;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestMethod;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

import java.time.Year;
import java.util.List;
import java.util.LinkedHashMap;
import java.util.Map;
import java.util.Set;

@RestController
@RequestMapping("/api/client")
public class ClientQuestionnaireController {

    private static final Logger log = LoggerFactory.getLogger(ClientQuestionnaireController.class);

    private final QuestionnaireService questionnaireService;
    private final AssessmentService assessmentService;
    private final ClientEntitlementService entitlementService;

    public ClientQuestionnaireController(
            QuestionnaireService questionnaireService,
            AssessmentService assessmentService,
            ClientEntitlementService entitlementService
    ) {
        this.questionnaireService = questionnaireService;
        this.assessmentService = assessmentService;
        this.entitlementService = entitlementService;
    }

    @GetMapping("/questionnaire")
    public QuestionnaireResponse questionnaire(@AuthenticationPrincipal Jwt jwt) {
        String email = jwt.getSubject();
        ClientProjectEntitlements entitlements = entitlementService.entitlementsForClientEmail(email);
        QuestionnaireResponse response = questionnaireService.getQuestionnaire(entitlements);
        entitlementService.logQuestionnaireAccess(email, response);
        if (response.segments().isEmpty()) {
            log.warn("Client questionnaire empty for user={} — check APP_QUESTIONNAIRE_SEED_ENABLED", email);
        }
        return response;
    }

    @GetMapping("/entitlements")
    public Map<String, Object> entitlements(@AuthenticationPrincipal Jwt jwt) {
        ClientProjectEntitlements e = entitlementService.entitlementsForClientEmail(jwt.getSubject());
        Set<Framework> allowed = e.builtinFrameworks();
        Map<String, Object> m = new LinkedHashMap<>();
        m.put("ndi", allowed.contains(Framework.NDI));
        m.put("cmmi", allowed.contains(Framework.CMMI));
        m.put("customMaturityFrameworkIds", e.customMaturityFrameworkIds());
        return m;
    }

    @PostMapping("/assessments")
    public Map<String, Object> createAssessment(
            @AuthenticationPrincipal Jwt jwt,
            @RequestBody(required = false) @Valid CreateAssessmentRequest request
    ) {
        int year = request == null ? Year.now().getValue() : request.year();
        Assessment assessment = assessmentService.createOrGetAssessmentForYear(jwt.getSubject(), year);
        return Map.of(
                "assessmentId", assessment.getId(),
                "year", assessment.getYear(),
                "version", assessment.getVersion(),
                "status", assessment.getStatus().name()
        );
    }

    @GetMapping("/assessment-versions")
    public List<AssessmentVersionSummaryDto> listAssessmentVersions(
            @AuthenticationPrincipal Jwt jwt,
            @RequestParam(required = false) Integer year
    ) {
        return assessmentService.listVersionSummariesForConnectedClient(jwt.getSubject(), year);
    }

    @GetMapping("/assessment-versions/{assessmentId}")
    public AssessmentResponse getAssessmentVersion(
            @AuthenticationPrincipal Jwt jwt,
            @PathVariable Long assessmentId
    ) {
        return assessmentService.getAssessmentVersionForClient(assessmentId, jwt.getSubject());
    }

    @PostMapping("/assessments/{assessmentId}/submit")
    public AssessmentResponse submit(
            @AuthenticationPrincipal Jwt jwt,
            @PathVariable Long assessmentId,
            @RequestBody @Valid SubmitAnswersRequest request
    ) {
        return assessmentService.submitAnswers(assessmentId, jwt.getSubject(), request);
    }

    @RequestMapping(
            value = {
                    "/assessments/{assessmentId}/answers",
                    "/assessments/{assessmentId}/draft",
                    "/assessments/{assessmentId}/save"
            },
            method = {RequestMethod.POST, RequestMethod.PUT, RequestMethod.PATCH}
    )
    public AssessmentResponse saveDraftAnswers(
            @AuthenticationPrincipal Jwt jwt,
            @PathVariable Long assessmentId,
            @RequestBody @Valid SubmitAnswersRequest request
    ) {
        return assessmentService.saveDraftAnswers(assessmentId, jwt.getSubject(), request);
    }

    @GetMapping("/assessments/{assessmentId}")
    public AssessmentResponse getAssessment(
            @AuthenticationPrincipal Jwt jwt,
            @PathVariable Long assessmentId
    ) {
        return assessmentService.getAssessment(assessmentId, jwt.getSubject());
    }
}

