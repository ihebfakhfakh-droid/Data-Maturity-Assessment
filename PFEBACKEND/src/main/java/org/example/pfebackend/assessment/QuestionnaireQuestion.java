package org.example.pfebackend.assessment;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.FetchType;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.GenerationType;
import jakarta.persistence.Id;
import jakarta.persistence.JoinColumn;
import jakarta.persistence.ManyToOne;
import jakarta.persistence.Table;
import jakarta.persistence.UniqueConstraint;

@Entity
@Table(
        name = "question",
        uniqueConstraints = @UniqueConstraint(name = "uq_question_code", columnNames = "code")
)
public class QuestionnaireQuestion {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "sub_domain_id")
    private QuestionnaireSegment segment;

    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "domain_id")
    private QuestionnaireDomain domain;

    @Column(nullable = false, length = 120)
    private String code;

    @Column(nullable = false, length = 500)
    private String text;

    @Column(nullable = false)
    private int sortOrder;

    @Column(nullable = false)
    private boolean active = true;

    public Long getId() {
        return id;
    }

    public QuestionnaireSegment getSegment() {
        return segment;
    }

    public void setSegment(QuestionnaireSegment segment) {
        this.segment = segment;
    }

    public QuestionnaireDomain getDomain() {
        return domain;
    }

    public void setDomain(QuestionnaireDomain domain) {
        this.domain = domain;
    }

    public String getCode() {
        return code;
    }

    public void setCode(String code) {
        this.code = code;
    }

    public String getText() {
        return text;
    }

    public void setText(String text) {
        this.text = text;
    }

    public int getSortOrder() {
        return sortOrder;
    }

    public void setSortOrder(int sortOrder) {
        this.sortOrder = sortOrder;
    }

    public boolean isActive() {
        return active;
    }

    public void setActive(boolean active) {
        this.active = active;
    }
}

