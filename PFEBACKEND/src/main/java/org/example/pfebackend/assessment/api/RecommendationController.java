package org.example.pfebackend.assessment.api;

import jakarta.validation.Valid;
import org.example.pfebackend.assessment.RecommendationService;
import org.example.pfebackend.assessment.dto.RecommendationTargetRequest;
import org.example.pfebackend.assessment.dto.RecommendationTargetResponse;
import org.example.pfebackend.staff.StaffService;
import org.example.pfebackend.user.AppUser;
import org.springframework.http.HttpHeaders;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.security.oauth2.jwt.Jwt;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.PutMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api/admin/assessments")
public class RecommendationController {

    private final StaffService staffService;
    private final RecommendationService recommendationService;

    public RecommendationController(StaffService staffService, RecommendationService recommendationService) {
        this.staffService = staffService;
        this.recommendationService = recommendationService;
    }

    @PutMapping("/{assessmentId}/recommendation-target")
    public RecommendationTargetResponse setRecommendationTarget(
            @AuthenticationPrincipal Jwt jwt,
            @PathVariable Long assessmentId,
            @RequestBody @Valid RecommendationTargetRequest request
    ) {
        AppUser staff = staffService.requireStaffByEmail(jwt.getSubject());
        return recommendationService.setRecommendationTarget(staff, assessmentId, request);
    }

    /**
     * Success: PDF bytes. Errors are handled by {@code ApiExceptionHandler} as JSON,
     * so this mapping must not restrict {@code produces} to PDF only.
     */
    @PostMapping(
            value = "/{assessmentId}/recommendation-report",
            produces = {
                    MediaType.APPLICATION_PDF_VALUE,
                    MediaType.APPLICATION_JSON_VALUE,
                    "application/problem+json"
            }
    )
    public ResponseEntity<byte[]> generateRecommendationReport(
            @AuthenticationPrincipal Jwt jwt,
            @PathVariable Long assessmentId
    ) {
        AppUser staff = staffService.requireStaffByEmail(jwt.getSubject());
        RecommendationService.RecommendationReportResult result =
                recommendationService.generateRecommendationReport(staff, assessmentId);

        return ResponseEntity.ok()
                .contentType(MediaType.APPLICATION_PDF)
                .header(HttpHeaders.CONTENT_DISPOSITION, "attachment; filename=\"" + result.filename() + "\"")
                .body(result.pdfBytes());
    }
}
