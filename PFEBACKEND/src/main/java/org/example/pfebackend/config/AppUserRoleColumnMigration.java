package org.example.pfebackend.config;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.boot.CommandLineRunner;
import org.springframework.core.annotation.Order;
import org.springframework.stereotype.Component;

import javax.sql.DataSource;
import java.sql.Connection;
import java.sql.Statement;

/**
 * Small idempotent migrations for the legacy PostgreSQL schema.
 */
@Component
@Order(1)
public class AppUserRoleColumnMigration implements CommandLineRunner {

    private static final Logger log = LoggerFactory.getLogger(AppUserRoleColumnMigration.class);

    private final DataSource dataSource;

    public AppUserRoleColumnMigration(DataSource dataSource) {
        this.dataSource = dataSource;
    }

    @Override
    public void run(String... args) {
        try (Connection c = dataSource.getConnection(); Statement s = c.createStatement()) {
            s.execute("ALTER TABLE app_user ALTER COLUMN role TYPE VARCHAR(32) USING role::text::VARCHAR(32)");
            log.debug("app_user.role widened to VARCHAR(32)");
        } catch (Exception e) {
            log.debug("Skipping app_user.role migration: {}", e.getMessage());
        }

        try (Connection c = dataSource.getConnection(); Statement s = c.createStatement()) {
            s.execute("ALTER TABLE assessment_answer ADD COLUMN IF NOT EXISTS answered BOOLEAN NOT NULL DEFAULT FALSE");
            s.execute("""
                    UPDATE assessment_answer aa
                    SET answered = FALSE
                    WHERE score = 0
                      AND NOT EXISTS (
                          SELECT 1 FROM evidence e WHERE e.answer_id = aa.id
                      )
                    """);
            s.execute("UPDATE assessment_answer SET answered = TRUE WHERE answered = FALSE AND score > 0");
            log.debug("assessment_answer.answered ensured");
        } catch (Exception e) {
            log.debug("Skipping assessment_answer.answered migration: {}", e.getMessage());
        }

        try (Connection c = dataSource.getConnection(); Statement s = c.createStatement()) {
            s.execute("ALTER TABLE assessment ADD COLUMN IF NOT EXISTS submitted_by_id BIGINT");
            s.execute("ALTER TABLE assessment ADD COLUMN IF NOT EXISTS submitted_by_role VARCHAR(32)");
            s.execute("""
                    UPDATE assessment a
                    SET submitted_by_id = client_id,
                        submitted_by_role = 'CLIENT'
                    WHERE a.submitted_at IS NOT NULL
                      AND a.submitted_by_id IS NULL
                    """);
            try {
                s.execute("""
                        ALTER TABLE assessment
                        ADD CONSTRAINT fk_assessment_submitted_by
                        FOREIGN KEY (submitted_by_id) REFERENCES app_user(id)
                        """);
            } catch (Exception ignored) {
                // Constraint already exists or legacy rows cannot be constrained; columns are enough for traceability.
            }
            log.debug("assessment submission traceability columns ensured");
        } catch (Exception e) {
            log.debug("Skipping assessment submission traceability migration: {}", e.getMessage());
        }

        try (Connection c = dataSource.getConnection(); Statement s = c.createStatement()) {
            s.execute("ALTER TABLE question ADD COLUMN IF NOT EXISTS active BOOLEAN NOT NULL DEFAULT TRUE");
            s.execute("UPDATE question SET active = TRUE WHERE active IS NULL");
            s.execute("ALTER TABLE domain ADD COLUMN IF NOT EXISTS active BOOLEAN NOT NULL DEFAULT TRUE");
            s.execute("UPDATE domain SET active = TRUE WHERE active IS NULL");
            log.debug("question/domain active columns ensured");
        } catch (Exception e) {
            log.debug("Skipping active column migration: {}", e.getMessage());
        }

        try (Connection c = dataSource.getConnection(); Statement s = c.createStatement()) {
            s.execute("""
                    INSERT INTO framework(name, version, created_at)
                    SELECT 'NDI', '1', now()
                    WHERE NOT EXISTS (
                        SELECT 1 FROM framework WHERE lower(coalesce(name, '')) = 'ndi'
                    )
                    """);
            s.execute("""
                    INSERT INTO framework(name, version, created_at)
                    SELECT 'CMMI', '1', now()
                    WHERE NOT EXISTS (
                        SELECT 1 FROM framework WHERE lower(coalesce(name, '')) = 'cmmi'
                    )
                    """);
            log.debug("built-in framework rows ensured");
        } catch (Exception e) {
            log.debug("Skipping built-in framework migration: {}", e.getMessage());
        }
    }
}
