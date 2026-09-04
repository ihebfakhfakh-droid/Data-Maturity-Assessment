package org.example.pfebackend.evidence.api;

import org.example.pfebackend.evidence.Evidence;
import org.example.pfebackend.evidence.EvidenceService;
import org.example.pfebackend.evidence.dto.EvidenceUploadResponse;
import org.springframework.core.io.FileSystemResource;
import org.springframework.core.io.Resource;
import org.springframework.http.HttpHeaders;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.security.oauth2.jwt.Jwt;
import org.springframework.web.bind.annotation.DeleteMapping;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.multipart.MultipartFile;

import java.util.List;

@RestController
@RequestMapping("/api/client")
public class ClientEvidenceController {

    private final EvidenceService evidenceService;

    public ClientEvidenceController(EvidenceService evidenceService) {
        this.evidenceService = evidenceService;
    }

    /**
     * Upload evidence + score for a given question (client side).
     * Multipart form-data:
     * - score: int
     * - file: MultipartFile
     */
    @PostMapping(value = "/assessments/{assessmentId}/answers/{questionCode}/evidence", consumes = MediaType.MULTIPART_FORM_DATA_VALUE)
    public List<EvidenceUploadResponse> uploadEvidence(
            @AuthenticationPrincipal Jwt jwt,
            @PathVariable Long assessmentId,
            @PathVariable String questionCode,
            @RequestParam("score") int score,
            @RequestParam("file") MultipartFile[] files
    ) {
        return evidenceService.uploadEvidencesForAnswer(assessmentId, jwt.getSubject(), questionCode, score, files);
    }

    @GetMapping("/evidences/{evidenceId}/download")
    public ResponseEntity<Resource> download(
            @AuthenticationPrincipal Jwt jwt,
            @PathVariable Long evidenceId
    ) {
        Evidence ev = evidenceService.loadEvidenceForClient(evidenceId, jwt.getSubject());
        var path = evidenceService.resolveStoragePath(ev.getStoragePath());
        Resource resource = new FileSystemResource(path);
        return ResponseEntity.ok()
                .contentType(MediaType.parseMediaType(ev.getContentType()))
                .header(HttpHeaders.CONTENT_DISPOSITION, "attachment; filename=\"" + ev.getOriginalFileName() + "\"")
                .body(resource);
    }

    @DeleteMapping("/evidences/{evidenceId}")
    public ResponseEntity<Void> delete(
            @AuthenticationPrincipal Jwt jwt,
            @PathVariable Long evidenceId
    ) {
        evidenceService.deleteEvidence(evidenceId, jwt.getSubject());
        return ResponseEntity.noContent().build();
    }
}

