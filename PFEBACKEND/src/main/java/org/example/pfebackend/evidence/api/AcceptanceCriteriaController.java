package org.example.pfebackend.evidence.api;

import org.example.pfebackend.evidence.AcceptanceCriteriaReportService;
import org.example.pfebackend.staff.StaffService;
import org.example.pfebackend.user.AppUser;
import org.springframework.http.HttpHeaders;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.security.access.prepost.PreAuthorize;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.security.oauth2.jwt.Jwt;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

/**
 * Staff-only Acceptance Criteria PDF generation (CONSULTANT / MANAGER).
 * React → this controller → Python microservice → PDF bytes.
 */
@RestController
@RequestMapping("/api/staff/evidences")
public class AcceptanceCriteriaController {

    private final StaffService staffService;
    private final AcceptanceCriteriaReportService acceptanceCriteriaReportService;

    public AcceptanceCriteriaController(
            StaffService staffService,
            AcceptanceCriteriaReportService acceptanceCriteriaReportService
    ) {
        this.staffService = staffService;
        this.acceptanceCriteriaReportService = acceptanceCriteriaReportService;
    }

    /**
     * Success: PDF bytes. Errors are JSON via {@code ApiExceptionHandler},
     * so {@code produces} must not be PDF-only.
     */
    @PreAuthorize("hasAnyRole('CONSULTANT', 'MANAGER')")
    @PostMapping(
            value = "/{evidenceId}/acceptance-criteria-report",
            produces = {
                    MediaType.APPLICATION_PDF_VALUE,
                    MediaType.APPLICATION_JSON_VALUE,
                    "application/problem+json"
            }
    )
    public ResponseEntity<byte[]> generateAcceptanceCriteriaReport(
            @AuthenticationPrincipal Jwt jwt,
            @PathVariable Long evidenceId
    ) {
        AppUser staff = staffService.requireStaffByEmail(jwt.getSubject());
        AcceptanceCriteriaReportService.AcceptanceCriteriaReportResult result =
                acceptanceCriteriaReportService.generateReport(staff, evidenceId);

        return ResponseEntity.ok()
                .contentType(MediaType.APPLICATION_PDF)
                .header(HttpHeaders.CONTENT_DISPOSITION, "attachment; filename=\"" + result.filename() + "\"")
                .body(result.pdfBytes());
    }
}
