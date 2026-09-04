package org.example.pfebackend.assessment;

import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;

import java.util.List;
import java.util.Optional;

public interface AssessmentAnswerRepository extends JpaRepository<AssessmentAnswer, Long> {
    Optional<AssessmentAnswer> findByAssessment_IdAndQuestion_Code(Long assessmentId, String questionCode);

    Optional<AssessmentAnswer> findByAssessment_IdAndQuestion_Id(Long assessmentId, Long questionId);

    @Query("""
            select distinct a from AssessmentAnswer a
            join fetch a.question q
            left join fetch q.segment s
            left join fetch a.evidences e
            where a.assessment.id = :assessmentId
            """)
    List<AssessmentAnswer> findByAssessment_Id(@Param("assessmentId") Long assessmentId);
}

