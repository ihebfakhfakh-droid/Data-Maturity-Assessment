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

@Entity
@Table(name = "sub_domain")
public class QuestionnaireSegment {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(name = "code", length = 80)
    private String code;

    @Column(name = "name", length = 200)
    private String title;

    @Column(name = "sort_order", nullable = false)
    private int sortOrder;

    @Column(name = "weight")
    private Double weight;

    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "domain_id")
    private QuestionnaireDomain domain;

    /** When set, this segment belongs to an admin-defined maturity framework (not built-in NDI/CMMI). */
    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "maturity_framework_id")
    private MaturityFrameworkDefinition maturityFramework;

    /** Optional parent segment (domain → sub-domain hierarchy). */
    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "parent_segment_id")
    private QuestionnaireSegment parent;

    public Long getId() {
        return id;
    }

    public String getCode() {
        return code;
    }

    public void setCode(String code) {
        this.code = code;
    }

    public String getTitle() {
        return title == null || title.isBlank() ? "Domain " + id : title;
    }

    public void setTitle(String title) {
        this.title = title;
    }

    public int getSortOrder() {
        return sortOrder;
    }

    public void setSortOrder(int sortOrder) {
        this.sortOrder = sortOrder;
    }

    public Double getWeight() {
        return weight;
    }

    public void setWeight(Double weight) {
        this.weight = weight;
    }

    public QuestionnaireDomain getDomain() {
        return domain;
    }

    public void setDomain(QuestionnaireDomain domain) {
        this.domain = domain;
    }

    public MaturityFrameworkDefinition getMaturityFramework() {
        return maturityFramework;
    }

    public void setMaturityFramework(MaturityFrameworkDefinition maturityFramework) {
        this.maturityFramework = maturityFramework;
    }

    public QuestionnaireSegment getParent() {
        return parent;
    }

    public void setParent(QuestionnaireSegment parent) {
        this.parent = parent;
    }
}

