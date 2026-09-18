package org.example.pfebackend.assessment.api;

import org.example.pfebackend.assessment.Assessment;
import org.example.pfebackend.assessment.AssessmentRepository;
import org.example.pfebackend.assessment.AssessmentService;
import org.example.pfebackend.assessment.dto.AssessmentResponse;
import org.example.pfebackend.assessment.dto.AssessmentVersionSummaryDto;
import org.example.pfebackend.assessment.dto.CompareVersionsResponse;
import org.example.pfebackend.staff.StaffService;
import org.example.pfebackend.user.AppUser;
import org.example.pfebackend.user.AppUserRepository;
import org.springframework.http.HttpStatus;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.security.oauth2.jwt.Jwt;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.server.ResponseStatusException;

import java.time.Year;
import java.util.List;

/**
 * Routes attendues par l’UI admin : {@code /api/admin/clients/.../assessment-versions} (hors préfixe {@code /staff}).
 */
@RestController
public class AdminClientAssessmentCompatController {

    private final StaffService staffService;
    private final AppUserRepository userRepository;
    private final AssessmentRepository assessmentRepository;
    private final AssessmentService assessmentService;

    public AdminClientAssessmentCompatController(
            StaffService staffService,
            AppUserRepository userRepository,
            AssessmentRepository assessmentRepository,
            AssessmentService assessmentService
    ) {
        this.staffService = staffService;
        this.userRepository = userRepository;
        this.assessmentRepository = assessmentRepository;
        this.assessmentService = assessmentService;
    }

    /**
     * Compare deux versions : soit {@code year}+{@code fromVersion}+{@code toVersion},
     * soit {@code fromAssessmentId}+{@code toAssessmentId} (clés primaires {@code assessments.id}).
     */
    @GetMapping("/api/admin/clients/{clientId}/assessment-versions/compare")
    public CompareVersionsResponse compareVersions(
            @AuthenticationPrincipal Jwt jwt,
            @PathVariable Long clientId,
            @RequestParam(required = false) Integer year,
            @RequestParam(required = false) Integer fromVersion,
            @RequestParam(required = false) Integer toVersion,
            @RequestParam(required = false) Long fromAssessmentId,
            @RequestParam(required = false) Long toAssessmentId
    ) {
        AppUser staff = staffService.requireStaffByEmail(jwt.getSubject());
        AppUser client = userRepository.findById(clientId)
                .orElseThrow(() -> new ResponseStatusException(HttpStatus.NOT_FOUND, "Client not found"));
        staffService.assertCanViewAssessmentVersions(staff, client);

        if (fromAssessmentId != null && toAssessmentId != null) {
            return assessmentService.compareByAssessmentIds(clientId, fromAssessmentId, toAssessmentId);
        }
        if (year != null && fromVersion != null && toVersion != null) {
            return assessmentService.compareVersionsForClientYear(clientId, year, fromVersion, toVersion);
        }
        throw new ResponseStatusException(
                HttpStatus.BAD_REQUEST,
                "Provide either (fromAssessmentId, toAssessmentId) or (year, fromVersion, toVersion). "
                        + "Example: ?year=2026&fromVersion=1&toVersion=2"
        );
    }

    @GetMapping("/api/admin/clients/{clientId}/assessment-versions")
    public List<AssessmentVersionSummaryDto> listVersions(
            @AuthenticationPrincipal Jwt jwt,
            @PathVariable Long clientId,
            @RequestParam(required = false) Integer year
    ) {
        AppUser staff = staffService.requireStaffByEmail(jwt.getSubject());
        AppUser client = userRepository.findById(clientId)
                .orElseThrow(() -> new ResponseStatusException(HttpStatus.NOT_FOUND, "Client not found"));
        staffService.assertCanViewAssessmentVersions(staff, client);
        int y = year != null ? year : Year.now().getValue();
        return assessmentService.listVersionSummariesForClientYear(clientId, y);
    }

    @GetMapping("/api/admin/clients/{clientId}/assessment-versions/{assessmentId}")
    public AssessmentResponse getVersionDetail(
            @AuthenticationPrincipal Jwt jwt,
            @PathVariable Long clientId,
            @PathVariable Long assessmentId
    ) {
        AppUser staff = staffService.requireStaffByEmail(jwt.getSubject());
        AppUser client = userRepository.findById(clientId)
                .orElseThrow(() -> new ResponseStatusException(HttpStatus.NOT_FOUND, "Client not found"));
        staffService.assertCanViewAssessmentVersions(staff, client);

        Assessment assessment = assessmentRepository.findById(assessmentId)
                .orElseThrow(() -> new ResponseStatusException(HttpStatus.NOT_FOUND, "Assessment not found"));
        if (!assessment.getClient().getId().equals(clientId)) {
            throw new ResponseStatusException(HttpStatus.NOT_FOUND, "Assessment not found for this client");
        }
        staffService.assertCanAccessAssessment(staff, assessment);
        return assessmentService.renderAssessment(assessment);
    }
}
