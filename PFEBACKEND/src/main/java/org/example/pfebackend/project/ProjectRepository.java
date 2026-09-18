package org.example.pfebackend.project;

import org.example.pfebackend.user.AppUser;
import org.jspecify.annotations.NonNull;
import org.springframework.data.jpa.repository.JpaRepository;

import java.util.Optional;

public interface ProjectRepository extends JpaRepository<@NonNull Project, @NonNull Long> {
    Optional<Project> findTopByClientOrderByCreatedAtDesc(AppUser client);
}

