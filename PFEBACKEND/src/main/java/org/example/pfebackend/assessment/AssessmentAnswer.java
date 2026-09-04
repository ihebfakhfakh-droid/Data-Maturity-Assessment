package org.example.pfebackend.assessment;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.Enumerated;
import jakarta.persistence.FetchType;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.GenerationType;
import jakarta.persistence.Id;
import jakarta.persistence.JoinColumn;
import jakarta.persistence.ManyToOne;
import jakarta.persistence.OneToMany;
import jakarta.persistence.PrePersist;
import jakarta.persistence.Table;
import jakarta.persistence.UniqueConstraint;
import org.example.pfebackend.evidence.Evidence;
import org.example.pfebackend.evidence.EvidenceRating;
import org.example.pfebackend.user.AppUser;

import java.time.Instant;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.List;

@Entity
@Table(
        name = "assessment_answer",
        uniqueConstraints = @UniqueConstraint(
                name = "uq_answer_assessment_question",
                columnNames = {"assessment_id", "question_id"}
        )
)
public class AssessmentAnswer {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @ManyToOne(fetch = FetchType.LAZY, optional = false)
    @JoinColumn(name = "assessment_id", nullable = false)
    private Assessment assessment;

    @ManyToOne(fetch = FetchType.LAZY, optional = false)
    @JoinColumn(name = "question_id", nullable = false)
    private QuestionnaireQuestion question;

    @Column(nullable = false)
    private int score; // 1..5

    /** Dernière date à laquelle le score (ou la ligne de réponse) a été enregistrée ou modifiée — historique. */
    @Column(name = "answered_at", nullable = false)
    private Instant answeredAt;

    @Column(nullable = false)
    private boolean answered;

    @Column(name = "note", length = 1000)
    private String note;

    @OneToMany(mappedBy = "answer", fetch = FetchType.LAZY)
    private List<Evidence> evidences = new ArrayList<>();

    @Enumerated(jakarta.persistence.EnumType.STRING)
    @Column(name = "evidence_staff_rating", length = 20)
    private EvidenceRating evidenceStaffRating;

    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "evidence_rated_by_id")
    private AppUser evidenceRatedBy;

    @Column(name = "evidence_rated_at")
    private Instant evidenceRatedAt;

    @Column(name = "evidence_staff_comment", length = 1000)
    private String evidenceStaffComment;

    @PrePersist
    void onCreateAnsweredAt() {
        if (answeredAt == null) {
            answeredAt = Instant.now();
        }
    }

    public Long getId() {
        return id;
    }

    public Assessment getAssessment() {
        return assessment;
    }

    public void setAssessment(Assessment assessment) {
        this.assessment = assessment;
    }

    public QuestionnaireQuestion getQuestion() {
        return question;
    }

    public void setQuestion(QuestionnaireQuestion question) {
        this.question = question;
    }

    public int getScore() {
        return score;
    }

    public void setScore(int score) {
        this.score = score;
    }

    public Instant getAnsweredAt() {
        return answeredAt;
    }

    public void setAnsweredAt(Instant answeredAt) {
        this.answeredAt = answeredAt;
    }

    public boolean isAnswered() {
        return answered;
    }

    public void setAnswered(boolean answered) {
        this.answered = answered;
    }

    public String getNote() {
        return note;
    }

    public void setNote(String note) {
        this.note = note;
    }

    public Evidence getEvidence() {
        return evidences == null
                ? null
                : evidences.stream()
                        .sorted(Comparator
                                .comparing(Evidence::getCreatedAt, Comparator.nullsLast(Instant::compareTo))
                                .thenComparing(Evidence::getId, Comparator.nullsLast(Long::compareTo)))
                        .findFirst()
                        .orElse(null);
    }

    public void setEvidence(Evidence evidence) {
        this.evidences = evidence == null ? new ArrayList<>() : new ArrayList<>(List.of(evidence));
    }

    public List<Evidence> getEvidences() {
        return evidences;
    }

    public void setEvidences(List<Evidence> evidences) {
        this.evidences = evidences == null ? new ArrayList<>() : evidences;
    }

    public EvidenceRating getEvidenceStaffRating() {
        return evidenceStaffRating;
    }

    public void setEvidenceStaffRating(EvidenceRating evidenceStaffRating) {
        this.evidenceStaffRating = evidenceStaffRating;
    }

    public AppUser getEvidenceRatedBy() {
        return evidenceRatedBy;
    }

    public void setEvidenceRatedBy(AppUser evidenceRatedBy) {
        this.evidenceRatedBy = evidenceRatedBy;
    }

    public Instant getEvidenceRatedAt() {
        return evidenceRatedAt;
    }

    public void setEvidenceRatedAt(Instant evidenceRatedAt) {
        this.evidenceRatedAt = evidenceRatedAt;
    }

    public String getEvidenceStaffComment() {
        return evidenceStaffComment;
    }

    public void setEvidenceStaffComment(String evidenceStaffComment) {
        this.evidenceStaffComment = evidenceStaffComment;
    }
}

