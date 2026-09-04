package org.example.pfebackend.evidence;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.EnumType;
import jakarta.persistence.Enumerated;
import jakarta.persistence.FetchType;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.GenerationType;
import jakarta.persistence.Id;
import jakarta.persistence.JoinColumn;
import jakarta.persistence.ManyToOne;
import jakarta.persistence.PrePersist;
import jakarta.persistence.Table;
import jakarta.persistence.Transient;
import org.example.pfebackend.assessment.AssessmentAnswer;
import org.example.pfebackend.user.AppUser;

import java.time.Instant;

@Entity
@Table(name = "evidence")
public class Evidence {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @ManyToOne(fetch = FetchType.LAZY, optional = false)
    @JoinColumn(name = "answer_id", nullable = false)
    private AssessmentAnswer answer;

    @ManyToOne(fetch = FetchType.LAZY, optional = false)
    @JoinColumn(name = "uploaded_by_id", nullable = false)
    private AppUser uploadedBy;

    @Column(nullable = false, length = 255)
    private String originalFileName;

    @Transient
    private String contentType;

    @Transient
    private long sizeBytes;

    /** Relative path under {@code app.evidence.storage-dir}. */
    @Column(nullable = false, length = 500)
    private String storagePath;

    @Enumerated(EnumType.STRING)
    @Column(length = 20)
    private EvidenceRating staffRating;

    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "rated_by_id")
    private AppUser ratedBy;

    @Transient
    private Instant ratedAt;

    @Transient
    private String staffComment;

    @Column(nullable = false, updatable = false)
    private Instant createdAt;

    @PrePersist
    void onCreate() {
        this.createdAt = Instant.now();
    }

    public Long getId() {
        return id;
    }

    public AssessmentAnswer getAnswer() {
        return answer;
    }

    public void setAnswer(AssessmentAnswer answer) {
        this.answer = answer;
    }

    public AppUser getUploadedBy() {
        return uploadedBy;
    }

    public void setUploadedBy(AppUser uploadedBy) {
        this.uploadedBy = uploadedBy;
    }

    public String getOriginalFileName() {
        return originalFileName;
    }

    public void setOriginalFileName(String originalFileName) {
        this.originalFileName = originalFileName;
    }

    public String getContentType() {
        return contentType == null || contentType.isBlank() ? "application/octet-stream" : contentType;
    }

    public void setContentType(String contentType) {
        this.contentType = contentType;
    }

    public long getSizeBytes() {
        return sizeBytes;
    }

    public void setSizeBytes(long sizeBytes) {
        this.sizeBytes = sizeBytes;
    }

    public String getStoragePath() {
        return storagePath;
    }

    public void setStoragePath(String storagePath) {
        this.storagePath = storagePath;
    }

    public EvidenceRating getStaffRating() {
        return staffRating;
    }

    public void setStaffRating(EvidenceRating staffRating) {
        this.staffRating = staffRating;
    }

    public AppUser getRatedBy() {
        return ratedBy;
    }

    public void setRatedBy(AppUser ratedBy) {
        this.ratedBy = ratedBy;
    }

    public Instant getRatedAt() {
        return ratedAt;
    }

    public void setRatedAt(Instant ratedAt) {
        this.ratedAt = ratedAt;
    }

    public String getStaffComment() {
        return staffComment;
    }

    public void setStaffComment(String staffComment) {
        this.staffComment = staffComment;
    }

    public Instant getCreatedAt() {
        return createdAt;
    }
}

