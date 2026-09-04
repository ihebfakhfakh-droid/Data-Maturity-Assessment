package org.example.pfebackend.evidence.api;

import jakarta.validation.Valid;
import org.example.pfebackend.evidence.Evidence;
import org.example.pfebackend.evidence.EvidenceService;
import org.example.pfebackend.evidence.dto.EvidenceUploadResponse;
import org.example.pfebackend.evidence.dto.RateEvidenceRequest;
import org.springframework.core.io.FileSystemResource;
import org.springframework.core.io.Resource;
import org.springframework.http.HttpHeaders;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.security.oauth2.jwt.Jwt;
import org.springframework.web.bind.annotation.DeleteMapping;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PatchMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.multipart.MultipartFile;

import java.util.List;

@RestController
@RequestMapping("/api/admin")
public class AdminEvidenceController {

    private final EvidenceService evidenceService;

    public AdminEvidenceController(EvidenceService evidenceService) {
        this.evidenceService = evidenceService;
    }

    @GetMapping("/evidences/{evidenceId}/download")
    public ResponseEntity<Resource> download(
            @AuthenticationPrincipal Jwt jwt,
            @PathVariable Long evidenceId
    ) {
        Evidence ev = evidenceService.loadEvidenceForStaff(evidenceId, jwt.getSubject());
        var path = evidenceService.resolveStoragePath(ev.getStoragePath());
        Resource resource = new FileSystemResource(path);
        return ResponseEntity.ok()
                .contentType(MediaType.parseMediaType(ev.getContentType()))
                .header(HttpHeaders.CONTENT_DISPOSITION, "attachment; filename=\"" + ev.getOriginalFileName() + "\"")
                .body(resource);
    }

    @PatchMapping("/evidences/{evidenceId}/rating")
    public void rate(
            @AuthenticationPrincipal Jwt jwt,
            @PathVariable Long evidenceId,
            @RequestBody @Valid RateEvidenceRequest request
    ) {
        evidenceService.rateEvidence(evidenceId, jwt.getSubject(), request);
    }

    @DeleteMapping("/evidences/{evidenceId}")
    public ResponseEntity<Void> delete(
            @AuthenticationPrincipal Jwt jwt,
            @PathVariable Long evidenceId
    ) {
        evidenceService.deleteEvidence(evidenceId, jwt.getSubject());
        return ResponseEntity.noContent().build();
    }

    /**
     * Staff upload evidence for an assessment answer.
     * Multipart form-data:
     * - score: int
     * - file: MultipartFile
     */
    @PostMapping(
            value = "/assessments/{assessmentId}/answers/{questionCode}/evidence",
            consumes = MediaType.MULTIPART_FORM_DATA_VALUE
    )
    public List<EvidenceUploadResponse> uploadEvidence(
            @AuthenticationPrincipal Jwt jwt,
            @PathVariable Long assessmentId,
            @PathVariable String questionCode,
            @RequestParam("score") int score,
            @RequestParam("file") MultipartFile[] files
    ) {
        return evidenceService.uploadEvidencesForAnswerAsStaff(assessmentId, jwt.getSubject(), questionCode, score, files);
    }
}
