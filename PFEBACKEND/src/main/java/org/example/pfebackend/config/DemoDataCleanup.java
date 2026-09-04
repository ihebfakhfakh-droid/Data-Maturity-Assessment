package org.example.pfebackend.config;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.boot.CommandLineRunner;
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.core.annotation.Order;
import org.springframework.stereotype.Component;
import org.springframework.transaction.annotation.Transactional;

@Component
@ConditionalOnProperty(name = "app.demo.cleanup.enabled", havingValue = "true")
@Order(90)
public class DemoDataCleanup implements CommandLineRunner {

    private static final Logger log = LoggerFactory.getLogger(DemoDataCleanup.class);

    private final DemoAccountMaintenance maintenance;

    public DemoDataCleanup(DemoAccountMaintenance maintenance) {
        this.maintenance = maintenance;
    }

    @Override
    @Transactional
    public void run(String... args) {
        log.info("Demo cleanup started (keeps imported projects, assessments and answers for demo clients)");
        maintenance.purgeNonDemoAccounts();
        maintenance.ensureDemoAccessRelationships();
        log.info("Demo cleanup finished");
    }
}
