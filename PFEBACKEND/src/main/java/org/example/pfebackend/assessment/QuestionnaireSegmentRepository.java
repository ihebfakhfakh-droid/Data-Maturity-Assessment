package org.example.pfebackend.assessment;

import org.springframework.data.jpa.repository.JpaRepository;

import java.util.Optional;

public interface QuestionnaireSegmentRepository extends JpaRepository<QuestionnaireSegment, Long> {
    Optional<QuestionnaireSegment> findByCode(String code);

    boolean existsByCodeIgnoreCase(String code);
}

