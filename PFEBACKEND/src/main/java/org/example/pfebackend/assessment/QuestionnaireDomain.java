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
@Table(name = "domain")
public class QuestionnaireDomain {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(name = "code", length = 80)
    private String code;

    @Column(name = "title", length = 240)
    private String title;

    @Column(name = "sort_order")
    private int sortOrder;

    @Column(name = "active")
    private boolean active = true;

    @Column(name = "weight")
    private Double weight;

    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "framework_id")
    private MaturityFrameworkDefinition maturityFramework;

    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "parent_segment_id")
    private QuestionnaireDomain parent;

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

    public boolean isActive() {
        return active;
    }

    public void setActive(boolean active) {
        this.active = active;
    }

    public Double getWeight() {
        return weight;
    }

    public void setWeight(Double weight) {
        this.weight = weight;
    }

    public MaturityFrameworkDefinition getMaturityFramework() {
        return maturityFramework;
    }

    public void setMaturityFramework(MaturityFrameworkDefinition maturityFramework) {
        this.maturityFramework = maturityFramework;
    }

    public QuestionnaireDomain getParent() {
        return parent;
    }

    public void setParent(QuestionnaireDomain parent) {
        this.parent = parent;
    }
}
