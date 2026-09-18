package org.example.pfebackend.project;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.FetchType;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.GenerationType;
import jakarta.persistence.Id;
import jakarta.persistence.JoinColumn;
import jakarta.persistence.JoinTable;
import jakarta.persistence.ManyToMany;
import jakarta.persistence.ManyToOne;
import jakarta.persistence.PrePersist;
import jakarta.persistence.Table;
import jakarta.persistence.Transient;
import org.example.pfebackend.user.AppUser;

import java.time.Instant;
import java.util.LinkedHashSet;
import java.util.Set;

@Entity
@Table(name = "project")
public class Project {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @ManyToOne(fetch = FetchType.LAZY, optional = false)
    @JoinColumn(name = "client_id", nullable = false)
    private AppUser client;

    @Column(nullable = false, length = 200)
    private String name;

    @ManyToMany(fetch = FetchType.LAZY)
    @JoinTable(
            name = "project_consultants",
            joinColumns = @JoinColumn(name = "project_id"),
            inverseJoinColumns = @JoinColumn(name = "consultant_id")
    )
    private Set<AppUser> consultants = new LinkedHashSet<>();

    @Transient
    private Set<Framework> frameworks = new LinkedHashSet<>();

    /** Admin-defined maturity frameworks ({@link org.example.pfebackend.assessment.MaturityFrameworkDefinition}) linked to this project. */
    @Transient
    private Set<Long> customMaturityFrameworkIds = new LinkedHashSet<>();

    @Column(nullable = false, updatable = false)
    private Instant createdAt;

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

    public String getName() {
        return name;
    }

    public void setName(String name) {
        this.name = name;
    }

    public Set<AppUser> getConsultants() {
        return consultants;
    }

    public void setConsultants(Set<AppUser> consultants) {
        this.consultants = consultants == null ? new LinkedHashSet<>() : new LinkedHashSet<>(consultants);
    }

    public Set<Framework> getFrameworks() {
        return frameworks;
    }

    public void setFrameworks(Set<Framework> frameworks) {
        this.frameworks = frameworks;
    }

    public Set<Long> getCustomMaturityFrameworkIds() {
        return customMaturityFrameworkIds;
    }

    public void setCustomMaturityFrameworkIds(Set<Long> customMaturityFrameworkIds) {
        this.customMaturityFrameworkIds = customMaturityFrameworkIds == null ? new LinkedHashSet<>() : new LinkedHashSet<>(customMaturityFrameworkIds);
    }

    public Instant getCreatedAt() {
        return createdAt;
    }
}

