package org.example.pfebackend.assessment;

import org.springframework.data.jpa.repository.JpaRepository;

import java.util.Collection;
import java.util.Optional;

public interface MaturityFrameworkDefinitionRepository extends JpaRepository<MaturityFrameworkDefinition, Long> {
    boolean existsByCodeIgnoreCase(String code);

    Optional<MaturityFrameworkDefinition> findByCodeIgnoreCase(String code);

    long countByIdIn(Collection<Long> ids);
}
