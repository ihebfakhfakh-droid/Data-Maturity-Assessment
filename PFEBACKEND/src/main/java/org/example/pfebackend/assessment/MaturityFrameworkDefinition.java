package org.example.pfebackend.assessment;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.EnumType;
import jakarta.persistence.Enumerated;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.GenerationType;
import jakarta.persistence.Id;
import jakarta.persistence.PrePersist;
import jakarta.persistence.Table;
import jakarta.persistence.UniqueConstraint;

import java.time.Instant;

@Entity
@Table(
        name = "framework",
        uniqueConstraints = @UniqueConstraint(name = "uq_maturity_framework_code", columnNames = "code")
)
public class MaturityFrameworkDefinition {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(nullable = false, length = 80)
    private String code;

    @Column(nullable = false, length = 200)
    private String name;

    @Enumerated(EnumType.STRING)
    @Column(nullable = false, length = 40)
    private DomainScoringMethod domainScoringMethod = DomainScoringMethod.DOMAIN_MINIMUM;

    @Enumerated(EnumType.STRING)
    @Column(nullable = false, length = 20)
    private FrameworkScoreScale scoreScale = FrameworkScoreScale.ZERO_TO_FIVE;

    @Column(nullable = false, updatable = false)
    private Instant createdAt;

    @PrePersist
    void onCreate() {
        this.createdAt = Instant.now();
    }

    public Long getId() {
        return id;
    }

    public String getCode() {
        return code;
    }

    public void setCode(String code) {
        this.code = code;
    }

    public String getName() {
        return name;
    }

    public void setName(String name) {
        this.name = name;
    }

    public DomainScoringMethod getDomainScoringMethod() {
        return domainScoringMethod;
    }

    public void setDomainScoringMethod(DomainScoringMethod domainScoringMethod) {
        this.domainScoringMethod = domainScoringMethod;
    }

    public FrameworkScoreScale getScoreScale() {
        return scoreScale;
    }

    public void setScoreScale(FrameworkScoreScale scoreScale) {
        this.scoreScale = scoreScale;
    }

    public Instant getCreatedAt() {
        return createdAt;
    }
}
