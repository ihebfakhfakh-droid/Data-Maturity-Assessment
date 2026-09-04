package org.example.pfebackend.assessment;

import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;

import java.util.List;
import java.util.Optional;

public interface QuestionnaireQuestionRepository extends JpaRepository<QuestionnaireQuestion, Long> {
    Optional<QuestionnaireQuestion> findByCode(String code);

    boolean existsByCodeIgnoreCase(String code);

    @Query("""
            select q from QuestionnaireQuestion q
            left join fetch q.segment s
            left join fetch q.domain d
            left join fetch s.domain sd
            where q.active = true
            order by q.sortOrder asc
            """)
    List<QuestionnaireQuestion> findByActiveTrueOrderBySegment_SortOrderAscSegment_CodeAscSortOrderAsc();
}

