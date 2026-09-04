package org.example.pfebackend.assessment;

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
import jakarta.persistence.UniqueConstraint;
import org.example.pfebackend.project.Project;
import org.example.pfebackend.user.AppUser;
import org.example.pfebackend.user.Role;

import java.time.Instant;

@Entity
@Table(
        name = "assessment",
        uniqueConstraints = @UniqueConstraint(
                name = "uq_assessment_client_year_version",
                columnNames = {"client_id", "year", "version"}
        )
)
public class Assessment {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @ManyToOne(fetch = FetchType.LAZY, optional = false)
    @JoinColumn(name = "client_id", nullable = false)
    private AppUser client;

    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "project_id")
    private Project project;

    @Column(name = "year", nullable = false)
    private int year;

    @Column(name = "version", nullable = false)
    private int version = 1;

    @Enumerated(EnumType.STRING)
    @Column(nullable = false, length = 20)
    private AssessmentStatus status = AssessmentStatus.DRAFT;

    @Column(name = "is_submitted", nullable = false)
    private boolean submitted;

    @Column(nullable = false, updatable = false)
    private Instant createdAt;

    private Instant submittedAt;

    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "submitted_by_id")
    private AppUser submittedBy;

    @Enumerated(EnumType.STRING)
    @Column(name = "submitted_by_role", length = 32)
    private Role submittedByRole;

    @Column(name = "version_comment", length = 1000)
    private String versionComment;

    /** Target global score for AI recommendations (persisted per assessment version). */
    @Column(name = "recommendation_target_score")
    private Double recommendationTargetScore;

    @PrePersist
    void onCreate() {
        this.createdAt = Instant.now();
    }

    public Long getId() {
        return id;
    }

    public AppUser getClient() {
        return client;
    }

    public void setClient(AppUser client) {
        this.client = client;
    }

    public Project getProject() {
        return project;
    }

    public void setProject(Project project) {
        this.project = project;
    }

    public int getYear() {
        return year;
    }

    public void setYear(int year) {
        this.year = year;
    }

    public int getVersion() {
        return version;
    }

    public void setVersion(int version) {
        this.version = version;
    }

    public AssessmentStatus getStatus() {
        return status;
    }

    public void setStatus(AssessmentStatus status) {
        this.status = status;
        this.submitted = status == AssessmentStatus.SUBMITTED;
    }

    public boolean isSubmitted() {
        return submitted;
    }

    public void setSubmitted(boolean submitted) {
        this.submitted = submitted;
        this.status = submitted ? AssessmentStatus.SUBMITTED : AssessmentStatus.DRAFT;
    }

    public Instant getCreatedAt() {
        return createdAt;
    }

    public Instant getSubmittedAt() {
        return submittedAt;
    }

    public void setSubmittedAt(Instant submittedAt) {
        this.submittedAt = submittedAt;
    }

    public AppUser getSubmittedBy() {
        return submittedBy;
    }

    public void setSubmittedBy(AppUser submittedBy) {
        this.submittedBy = submittedBy;
    }

    public Role getSubmittedByRole() {
        return submittedByRole;
    }

    public void setSubmittedByRole(Role submittedByRole) {
        this.submittedByRole = submittedByRole;
    }

    public String getVersionComment() {
        return versionComment;
    }

    public void setVersionComment(String versionComment) {
        this.versionComment = versionComment;
    }

    public Double getRecommendationTargetScore() {
        return recommendationTargetScore;
    }

    public void setRecommendationTargetScore(Double recommendationTargetScore) {
        this.recommendationTargetScore = recommendationTargetScore;
    }
}

