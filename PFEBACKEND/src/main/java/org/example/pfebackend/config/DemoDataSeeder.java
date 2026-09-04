package org.example.pfebackend.config;

import org.example.pfebackend.project.Framework;
import org.example.pfebackend.project.Project;
import org.example.pfebackend.project.ProjectRepository;
import org.example.pfebackend.user.AppUser;
import org.example.pfebackend.user.Role;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.boot.CommandLineRunner;
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.core.annotation.Order;
import org.springframework.core.io.ClassPathResource;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Component;
import org.springframework.transaction.annotation.Transactional;

import java.io.BufferedReader;
import java.io.InputStreamReader;
import java.nio.charset.StandardCharsets;
import java.time.Year;
import java.util.ArrayList;
import java.util.List;
import java.util.Locale;
import java.util.Optional;

/**
 * Synthetic demo data for empty Docker databases without a local snapshot import.
 * Disabled by default when using {@code local-snapshot.sql}.
 */
@Component
@ConditionalOnProperty(name = "app.demo.seed.synthetic", havingValue = "true")
@Order(100)
public class DemoDataSeeder implements CommandLineRunner {

    private static final Logger log = LoggerFactory.getLogger(DemoDataSeeder.class);

    private static final int DEMO_ASSESSMENT_VERSION = 1;
    private static final String DEMO_ANSWERS_RESOURCE = "db/demo-assessment-answers.csv";

    private final DemoAccountMaintenance maintenance;
    private final ProjectRepository projectRepository;
    private final JdbcTemplate jdbcTemplate;

    public DemoDataSeeder(
            DemoAccountMaintenance maintenance,
            ProjectRepository projectRepository,
            JdbcTemplate jdbcTemplate
    ) {
        this.maintenance = maintenance;
        this.projectRepository = projectRepository;
        this.jdbcTemplate = jdbcTemplate;
    }

    @Override
    @Transactional
    public void run(String... args) {
        log.info("Synthetic demo seed started");

        maintenance.purgeNonDemoAccounts();

        AppUser manager = maintenance.ensureUser(
                DemoAccountMaintenance.DEMO_MANAGER_EMAIL,
                "Omar Trabelsi",
                "123456omar",
                Role.MANAGER,
                null
        );
        AppUser consultant = maintenance.ensureUser(
                DemoAccountMaintenance.DEMO_CONSULTANT_EMAIL,
                "Mayssa Benjmaa",
                "123456mayssa",
                Role.CONSULTANT,
                manager
        );
        maintenance.ensureConsultantReportsToManager(consultant, manager);

        AppUser client1 = maintenance.ensureUser(
                DemoAccountMaintenance.DEMO_CLIENT1_EMAIL,
                "Oussema Lazez",
                "nsTp3U5hRkuE",
                Role.CLIENT,
                null
        );
        AppUser client2 = maintenance.ensureUser(
                DemoAccountMaintenance.DEMO_CLIENT2_EMAIL,
                "Youssef Benjmaa",
                "FUN8s#MbjR2M",
                Role.CLIENT,
                null
        );

        Project project1 = ensureProjectForClient(client1);
        Project project2 = ensureProjectForClient(client2);

        assignFrameworksIfMissing(project1.getId(), Framework.NDI, Framework.CMMI);
        assignFrameworksIfMissing(project2.getId(), Framework.NDI, Framework.CMMI);

        maintenance.assignConsultantIfMissing(project1.getId(), consultant.getId());
        maintenance.assignConsultantIfMissing(project2.getId(), consultant.getId());

        int assessmentYear = Year.now().getValue();
        ensureCurrentAssessment(client1.getId(), project1.getId(), assessmentYear);
        ensureCurrentAssessment(client2.getId(), project2.getId(), assessmentYear);
        int seededAnswers = seedDemoAssessmentAnswers(assessmentYear);

        log.info("Synthetic demo seed finished (answers inserted={})", seededAnswers);
    }

    private Project ensureProjectForClient(AppUser client) {
        Optional<Project> existing = projectRepository.findTopByClientOrderByCreatedAtDesc(client);
        if (existing.isPresent()) {
            return existing.get();
        }

        Project project = new Project();
        project.setClient(client);
        project.setName("Project - " + client.getFullName());
        return projectRepository.saveAndFlush(project);
    }

    private void assignFrameworksIfMissing(Long projectId, Framework... frameworks) {
        for (Framework framework : frameworks) {
            Long frameworkId = resolveFrameworkId(framework);
            if (frameworkId == null) {
                continue;
            }
            jdbcTemplate.update(
                    """
                            insert into project_framework(project_id, framework_id, assigned_at)
                            select ?, ?, now()
                            where not exists (
                                select 1
                                from project_framework
                                where project_id = ?
                                  and framework_id = ?
                            )
                            """,
                    projectId,
                    frameworkId,
                    projectId,
                    frameworkId
            );
        }
    }

    private Long resolveFrameworkId(Framework framework) {
        String code = framework.name().toLowerCase(Locale.ROOT);
        List<Long> ids = jdbcTemplate.queryForList(
                """
                        select id
                        from framework
                        where lower(coalesce(code, '')) = ?
                           or lower(coalesce(name, '')) = ?
                           or lower(coalesce(name, '')) like ?
                        order by id
                        limit 1
                        """,
                Long.class,
                code,
                code,
                "%" + code + "%"
        );
        return ids.isEmpty() ? null : ids.get(0);
    }

    private void ensureCurrentAssessment(Long clientId, Long projectId, int year) {
        List<Long> existing = jdbcTemplate.queryForList(
                """
                        select id
                        from assessment
                        where client_id = ?
                          and year = ?
                          and version = ?
                        """,
                Long.class,
                clientId,
                year,
                DEMO_ASSESSMENT_VERSION
        );
        if (!existing.isEmpty()) {
            return;
        }

        jdbcTemplate.update(
                """
                        insert into assessment (
                            client_id,
                            project_id,
                            year,
                            version,
                            status,
                            is_submitted,
                            created_at
                        )
                        values (?, ?, ?, ?, 'DRAFT', false, now())
                        """,
                clientId,
                projectId,
                year,
                DEMO_ASSESSMENT_VERSION
        );
    }

    private int seedDemoAssessmentAnswers(int year) {
        ClassPathResource resource = new ClassPathResource(DEMO_ANSWERS_RESOURCE);
        if (!resource.exists()) {
            return 0;
        }

        int inserted = 0;
        try (BufferedReader reader = new BufferedReader(
                new InputStreamReader(resource.getInputStream(), StandardCharsets.UTF_8)
        )) {
            String line;
            while ((line = reader.readLine()) != null) {
                if (line.isBlank()) {
                    continue;
                }
                DemoAnswerRow row = parseDemoAnswerRow(line);
                if (row == null) {
                    continue;
                }
                inserted += insertDemoAnswerIfMissing(row, year);
            }
        } catch (Exception ex) {
            throw new IllegalStateException("Failed to seed demo assessment answers from " + DEMO_ANSWERS_RESOURCE, ex);
        }
        return inserted;
    }

    private int insertDemoAnswerIfMissing(DemoAnswerRow row, int year) {
        boolean answered = row.score() > 0 && row.answered();
        return jdbcTemplate.update(
                """
                        insert into assessment_answer (
                            assessment_id,
                            question_id,
                            score,
                            answered_at,
                            answered,
                            note
                        )
                        select a.id, q.id, ?, ?::timestamptz, ?, ?
                        from assessment a
                        join app_user u on u.id = a.client_id
                        join question q on lower(q.code) = lower(?)
                        where lower(u.email) = ?
                          and a.year = ?
                          and a.version = ?
                          and not exists (
                              select 1
                              from assessment_answer aa
                              where aa.assessment_id = a.id
                                and aa.question_id = q.id
                          )
                        """,
                row.score(),
                row.answeredAtIso(),
                answered,
                row.note(),
                row.questionCode(),
                row.clientEmail(),
                year,
                DEMO_ASSESSMENT_VERSION
        );
    }

    private static DemoAnswerRow parseDemoAnswerRow(String line) {
        String[] parts = line.split(",", -1);
        if (parts.length < 6) {
            return null;
        }
        String clientEmail = DemoAccountMaintenance.normalizeEmail(parts[0]);
        String questionCode = parts[1].trim();
        int score = Integer.parseInt(parts[2].trim());
        boolean answered = "t".equalsIgnoreCase(parts[3].trim());
        String note = unquoteCsvField(parts[4]);
        if (note != null && note.isBlank()) {
            note = null;
        }
        return new DemoAnswerRow(clientEmail, questionCode, score, answered, note, parts[5].trim());
    }

    private static String unquoteCsvField(String value) {
        if (value == null) {
            return null;
        }
        String trimmed = value.trim();
        if (trimmed.length() >= 2 && trimmed.startsWith("\"") && trimmed.endsWith("\"")) {
            return trimmed.substring(1, trimmed.length() - 1);
        }
        return trimmed;
    }

    private record DemoAnswerRow(
            String clientEmail,
            String questionCode,
            int score,
            boolean answered,
            String note,
            String answeredAtIso
    ) {
    }
}
