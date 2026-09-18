package org.example.pfebackend.assessment;

import org.example.pfebackend.user.AppUser;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;

import java.util.List;
import java.util.Optional;

public interface AssessmentRepository extends JpaRepository<Assessment, Long> {

    Optional<Assessment> findFirstByClient_IdAndYearOrderByVersionDesc(Long clientId, int year);

    List<Assessment> findByClient_IdAndYearOrderByVersionAsc(Long clientId, int year);

    List<Assessment> findByClient_IdOrderByYearAscVersionAsc(Long clientId);

    Optional<Assessment> findByClient_IdAndYearAndVersion(Long clientId, int year, int version);

    List<Assessment> findByClientOrderByYearDescVersionDesc(AppUser client);

    Optional<Assessment> findFirstByClient_IdAndStatusOrderByYearDescVersionDesc(
            Long clientId,
            AssessmentStatus status
    );

    Optional<Assessment> findFirstByProject_IdAndStatusOrderByYearDescVersionDesc(
            Long projectId,
            AssessmentStatus status
    );

    @Query("""
            select a
            from Assessment a
            where a.client = :client
              and (
                (
                  a.status = :submittedStatus
                  and a.version = (
                    select max(s.version)
                    from Assessment s
                    where s.client = a.client
                      and s.year = a.year
                      and s.status = :submittedStatus
                  )
                )
                or (
                  a.status = :draftStatus
                  and not exists (
                    select s.id
                    from Assessment s
                    where s.client = a.client
                      and s.year = a.year
                      and s.status = :submittedStatus
                  )
                  and a.version = (
                    select max(d.version)
                    from Assessment d
                    where d.client = a.client
                      and d.year = a.year
                      and d.status = :draftStatus
                  )
                )
              )
            order by a.year desc, a.version desc
            """)
    List<Assessment> findMainAssessmentsByClient(
            @Param("client") AppUser client,
            @Param("submittedStatus") AssessmentStatus submittedStatus,
            @Param("draftStatus") AssessmentStatus draftStatus
    );
}

