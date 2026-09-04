package org.example.pfebackend.config;

import org.example.pfebackend.user.AppUser;
import org.example.pfebackend.user.AppUserRepository;
import org.example.pfebackend.user.Role;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.stereotype.Component;

import java.util.LinkedHashSet;
import java.util.List;
import java.util.Locale;
import java.util.Optional;
import java.util.Set;
import java.util.stream.Collectors;

@Component
class DemoAccountMaintenance {

    private static final Logger log = LoggerFactory.getLogger(DemoAccountMaintenance.class);

    static final String DEMO_MANAGER_EMAIL = "omartrabelsi@manager";
    static final String DEMO_CONSULTANT_EMAIL = "mayssabenjmaa@consultant";
    static final String DEMO_CLIENT1_EMAIL = "oussemalazez@client";
    static final String DEMO_CLIENT2_EMAIL = "youssefbenjmaa@client";

    private final AppUserRepository appUserRepository;
    private final PasswordEncoder passwordEncoder;
    private final JdbcTemplate jdbcTemplate;

    @Value("${app.auth.bootstrap.admin-email:admin@pfe.local}")
    private String adminEmail;

    DemoAccountMaintenance(
            AppUserRepository appUserRepository,
            PasswordEncoder passwordEncoder,
            JdbcTemplate jdbcTemplate
    ) {
        this.appUserRepository = appUserRepository;
        this.passwordEncoder = passwordEncoder;
        this.jdbcTemplate = jdbcTemplate;
    }

    void purgeNonDemoAccounts() {
        Set<String> keepEmails = demoKeepEmails();
        Object[] keepParams = keepEmails.toArray();
        String inClause = sqlInClause(keepEmails.size());

        List<Long> userIdsToRemove = jdbcTemplate.queryForList(
                "select id from app_user where lower(email) not in (" + inClause + ")",
                Long.class,
                keepParams
        );
        if (userIdsToRemove.isEmpty()) {
            log.info("Demo maintenance: no non-demo accounts to remove");
            return;
        }

        clearUserReferences(userIdsToRemove);

        List<Long> clientIdsToRemove = jdbcTemplate.queryForList(
                """
                        select id
                        from app_user
                        where lower(email) not in (%s)
                          and role = 'CLIENT'
                        """.formatted(inClause),
                Long.class,
                keepParams
        );
        for (Long clientId : clientIdsToRemove) {
            purgeClientData(clientId);
        }

        String userInClause = sqlInClause(userIdsToRemove.size());
        jdbcTemplate.update(
                "delete from project_consultants where consultant_id in (" + userInClause + ")",
                userIdsToRemove.toArray()
        );

        int removed = jdbcTemplate.update(
                "delete from app_user where lower(email) not in (" + inClause + ")",
                keepParams
        );
        log.info("Demo maintenance: removed {} non-demo account(s)", removed);
    }

    void ensureDemoAccessRelationships() {
        AppUser manager = requireDemoUser(DEMO_MANAGER_EMAIL, Role.MANAGER);
        AppUser consultant = requireDemoUser(DEMO_CONSULTANT_EMAIL, Role.CONSULTANT);
        ensureConsultantReportsToManager(consultant, manager);

        for (String clientEmail : List.of(DEMO_CLIENT1_EMAIL, DEMO_CLIENT2_EMAIL)) {
            AppUser client = requireDemoUser(clientEmail, Role.CLIENT);
            List<Long> projectIds = jdbcTemplate.queryForList(
                    "select id from project where client_id = ? order by id",
                    Long.class,
                    client.getId()
            );
            for (Long projectId : projectIds) {
                assignConsultantIfMissing(projectId, consultant.getId());
            }
            log.info(
                    "Demo maintenance: consultant {} linked to {} project(s) for client {}",
                    consultant.getEmail(),
                    projectIds.size(),
                    client.getEmail()
            );
        }

        log.info(
                "Demo maintenance: manager {} can access demo clients via consultant {}",
                manager.getEmail(),
                consultant.getEmail()
        );
    }

    AppUser ensureUser(String email, String fullName, String rawPassword, Role role, AppUser managedBy) {
        String normalizedEmail = normalizeEmail(email);
        Optional<AppUser> existing = appUserRepository.findByEmailIgnoreCase(normalizedEmail);
        if (existing.isPresent()) {
            AppUser user = existing.get();
            log.info("Demo maintenance: user {} already exists (id={})", normalizedEmail, user.getId());
            if (role == Role.CONSULTANT && managedBy != null) {
                ensureConsultantReportsToManager(user, managedBy);
            }
            return user;
        }

        AppUser user = new AppUser();
        user.setEmail(normalizedEmail);
        user.setFullName(fullName);
        user.setPassword(passwordEncoder.encode(rawPassword));
        user.setRole(role);
        if (managedBy != null) {
            user.setManagedBy(managedBy);
        }
        AppUser saved = appUserRepository.saveAndFlush(user);
        log.info("Demo maintenance: created {} user {} (id={})", role, normalizedEmail, saved.getId());
        return saved;
    }

    void ensureConsultantReportsToManager(AppUser consultant, AppUser manager) {
        if (consultant.getRole() != Role.CONSULTANT) {
            return;
        }
        if (consultant.getManagedBy() != null && consultant.getManagedBy().getId().equals(manager.getId())) {
            return;
        }
        consultant.setManagedBy(manager);
        appUserRepository.saveAndFlush(consultant);
        log.info("Demo maintenance: linked consultant {} to manager {}", consultant.getEmail(), manager.getEmail());
    }

    void assignConsultantIfMissing(Long projectId, Long consultantId) {
        int inserted = jdbcTemplate.update(
                """
                        insert into project_consultants(project_id, consultant_id, assigned_at, can_manage_project)
                        select ?, ?, now(), false
                        where not exists (
                            select 1
                            from project_consultants
                            where project_id = ?
                              and consultant_id = ?
                        )
                        """,
                projectId,
                consultantId,
                projectId,
                consultantId
        );
        if (inserted > 0) {
            log.info("Demo maintenance: assigned consultant {} to project {}", consultantId, projectId);
        }
    }

    private AppUser requireDemoUser(String email, Role role) {
        return appUserRepository.findByEmailIgnoreCase(normalizeEmail(email))
                .filter(user -> user.getRole() == role)
                .orElseThrow(() -> new IllegalStateException(
                        "Demo account missing after cleanup: " + email + " (" + role + ")"
                ));
    }

    private Set<String> demoKeepEmails() {
        Set<String> keep = new LinkedHashSet<>();
        keep.add(normalizeEmail(adminEmail));
        keep.add(normalizeEmail(DEMO_MANAGER_EMAIL));
        keep.add(normalizeEmail(DEMO_CONSULTANT_EMAIL));
        keep.add(normalizeEmail(DEMO_CLIENT1_EMAIL));
        keep.add(normalizeEmail(DEMO_CLIENT2_EMAIL));
        return keep;
    }

    private void purgeClientData(Long clientId) {
        jdbcTemplate.update(
                """
                        delete from evidence
                        where answer_id in (
                            select aa.id
                            from assessment_answer aa
                            join assessment a on a.id = aa.assessment_id
                            where a.client_id = ?
                        )
                        """,
                clientId
        );
        jdbcTemplate.update(
                """
                        delete from assessment_answer
                        where assessment_id in (
                            select id from assessment where client_id = ?
                        )
                        """,
                clientId
        );
        jdbcTemplate.update("delete from assessment where client_id = ?", clientId);
        jdbcTemplate.update(
                """
                        delete from project_framework
                        where project_id in (
                            select id from project where client_id = ?
                        )
                        """,
                clientId
        );
        jdbcTemplate.update(
                """
                        delete from project_consultants
                        where project_id in (
                            select id from project where client_id = ?
                        )
                        """,
                clientId
        );
        jdbcTemplate.update("delete from project where client_id = ?", clientId);
    }

    private void clearUserReferences(List<Long> userIds) {
        if (userIds.isEmpty()) {
            return;
        }
        String inClause = sqlInClause(userIds.size());
        Object[] ids = userIds.toArray();

        jdbcTemplate.update("update app_user set managed_by_id = null where managed_by_id in (" + inClause + ")", ids);
        reassignEvidenceUploaders(userIds);
        clearNullableUserReference("evidence", "rated_by_id", ids);
        clearNullableUserReference("assessment_answer", "evidence_rated_by_id", ids);
        clearNullableUserReference("assessment", "submitted_by_id", ids);
    }

    private void reassignEvidenceUploaders(List<Long> userIds) {
        if (!columnExists("evidence", "uploaded_by_id")) {
            return;
        }
        String inClause = sqlInClause(userIds.size());
        jdbcTemplate.update(
                """
                        update evidence e
                        set uploaded_by_id = a.client_id
                        from assessment_answer aa
                        join assessment a on a.id = aa.assessment_id
                        where e.answer_id = aa.id
                          and e.uploaded_by_id in (%s)
                        """.formatted(inClause),
                userIds.toArray()
        );
        jdbcTemplate.update(
                "delete from evidence where uploaded_by_id in (" + inClause + ")",
                userIds.toArray()
        );
    }

    private void clearNullableUserReference(String tableName, String columnName, Object[] userIds) {
        if (!columnExists(tableName, columnName)) {
            return;
        }
        String inClause = sqlInClause(userIds.length);
        jdbcTemplate.update(
                "update " + tableName + " set " + columnName + " = null where " + columnName + " in (" + inClause + ")",
                userIds
        );
    }

    private boolean columnExists(String tableName, String columnName) {
        Integer count = jdbcTemplate.queryForObject(
                """
                        select count(*)
                        from information_schema.columns
                        where table_schema = 'public'
                          and table_name = ?
                          and column_name = ?
                        """,
                Integer.class,
                tableName,
                columnName
        );
        return count != null && count > 0;
    }

    private static String sqlInClause(int size) {
        return java.util.Collections.nCopies(size, "?").stream().collect(Collectors.joining(", "));
    }

    static String normalizeEmail(String email) {
        return email == null ? "" : email.trim().toLowerCase(Locale.ROOT);
    }
}
