package org.example.pfebackend.user;

import org.example.pfebackend.assessment.AssessmentStatus;
import org.jspecify.annotations.NonNull;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;

import java.util.Collection;
import java.util.List;
import java.util.Optional;

public interface AppUserRepository extends JpaRepository<@NonNull AppUser, @NonNull Long> {
    Optional<AppUser> findByEmailIgnoreCase(String email);

    boolean existsByEmailIgnoreCase(String email);

    boolean existsByFullNameIgnoreCase(String fullName);

    List<AppUser> findByRole(Role role);

    List<AppUser> findByRoleAndManagedBy_Id(Role role, Long managerId);

    @Query("select distinct c from Project p join p.client c join p.consultants consultant "
            + "where consultant.id = :consultantId and c.role = 'CLIENT'")
    List<AppUser> findClientsAssignedToProjectConsultant(@Param("consultantId") Long consultantId);

    @Query("""
            select u
            from AppUser u
            where u.role in :roles
              and not exists (
                  select p.id
                  from Project p
                  join p.consultants assigned
                  where p.id = :projectId
                    and assigned.id = u.id
              )
            order by lower(coalesce(u.fullName, u.email)), u.id
            """)
    List<AppUser> findAvailableProjectAssignees(
            @Param("roles") Collection<Role> roles,
            @Param("projectId") Long projectId
    );

    @Query("select distinct c from Assessment a join a.client c "
            + "where a.status = :st and c.role = 'CLIENT'")
    List<AppUser> findDistinctClientsHavingAssessmentWithStatus(@Param("st") AssessmentStatus status);

    @Query("select distinct c from Assessment a join a.client c "
            + "where c.role = 'CLIENT'")
    List<AppUser> findDistinctClientsHavingAssessment();
}
