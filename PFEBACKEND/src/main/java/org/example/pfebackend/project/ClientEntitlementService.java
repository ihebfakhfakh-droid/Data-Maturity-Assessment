package org.example.pfebackend.project;

import org.example.pfebackend.assessment.dto.QuestionnaireResponse;
import org.example.pfebackend.user.AppUser;
import org.example.pfebackend.user.CommittedAppUserLoader;
import org.example.pfebackend.user.Role;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.http.HttpStatus;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.web.server.ResponseStatusException;

import java.util.LinkedHashSet;
import java.util.Locale;
import java.util.Optional;
import java.util.Set;

@Service
public class ClientEntitlementService {

    private static final Logger log = LoggerFactory.getLogger(ClientEntitlementService.class);

    private final CommittedAppUserLoader committedAppUserLoader;
    private final ProjectRepository projectRepository;
    private final JdbcTemplate jdbcTemplate;

    public ClientEntitlementService(
            CommittedAppUserLoader committedAppUserLoader,
            ProjectRepository projectRepository,
            JdbcTemplate jdbcTemplate
    ) {
        this.committedAppUserLoader = committedAppUserLoader;
        this.projectRepository = projectRepository;
        this.jdbcTemplate = jdbcTemplate;
    }

    @Transactional(readOnly = true)
    public ClientProjectEntitlements entitlementsForClientEmail(String clientEmail) {
        AppUser client = committedAppUserLoader.findByEmailInNewTransaction(normalizeEmail(clientEmail))
                .orElseThrow(() -> new ResponseStatusException(HttpStatus.UNAUTHORIZED, "User not found"));
        if (client.getRole() != Role.CLIENT) {
            throw new ResponseStatusException(HttpStatus.FORBIDDEN, "Client access only");
        }
        return projectRepository.findTopByClientOrderByCreatedAtDesc(client)
                .map(p -> {
                    Set<Framework> frameworks = loadBuiltinFrameworks(p.getId());
                    if (frameworks.isEmpty()) {
                        // Legacy rows may reference framework IDs/names we cannot resolve; avoid hiding the questionnaire.
                        frameworks = Set.of(Framework.NDI, Framework.CMMI);
                    }
                    return new ClientProjectEntitlements(frameworks, Set.of());
                })
                .orElseGet(() -> new ClientProjectEntitlements(Set.of(Framework.NDI, Framework.CMMI), Set.of()));
    }

    @Transactional(readOnly = true)
    public ClientProjectEntitlements entitlementsForProject(Long projectId) {
        if (projectId == null) {
            return new ClientProjectEntitlements(Set.of(), Set.of());
        }
        Set<Framework> frameworks = loadBuiltinFrameworks(projectId);
        if (frameworks.isEmpty()) {
            frameworks = Set.of(Framework.NDI, Framework.CMMI);
        }
        return new ClientProjectEntitlements(frameworks, Set.of());
    }

    @Transactional(readOnly = true)
    public Set<Framework> frameworksForClientEmail(String clientEmail) {
        return entitlementsForClientEmail(clientEmail).builtinFrameworks();
    }

    @Transactional(readOnly = true)
    public void logQuestionnaireAccess(String clientEmail, QuestionnaireResponse questionnaire) {
        String email = normalizeEmail(clientEmail);
        Optional<Project> project = committedAppUserLoader.findByEmailInNewTransaction(email)
                .flatMap(client -> projectRepository.findTopByClientOrderByCreatedAtDesc(client));
        ClientProjectEntitlements entitlements = entitlementsForClientEmail(email);
        Set<Framework> linked = project.map(p -> loadBuiltinFrameworks(p.getId())).orElse(Set.of());

        int ndiSegments = 0;
        int ndiQuestions = 0;
        int cmmiSegments = 0;
        int cmmiQuestions = 0;
        for (QuestionnaireResponse.SegmentDto segment : questionnaire.segments()) {
            int questionCount = segment.questions() == null ? 0 : segment.questions().size();
            String fw = segment.maturityFrameworkCode() == null ? "" : segment.maturityFrameworkCode().toUpperCase(Locale.ROOT);
            if (fw.contains("NDI") || segment.code() != null && segment.code().startsWith("ndi_")) {
                ndiSegments++;
                ndiQuestions += questionCount;
            } else if (fw.contains("CMMI") || segment.code() != null && segment.code().startsWith("cmmi_")) {
                cmmiSegments++;
                cmmiQuestions += questionCount;
            }
        }

        log.info(
                "Client questionnaire: user={}, projectId={}, projectName={}, linkedFrameworks={}, effectiveFrameworks={}, segments={}, questions={}, ndiSegments={}, ndiQuestions={}, cmmiSegments={}, cmmiQuestions={}",
                email,
                project.map(Project::getId).orElse(null),
                project.map(Project::getName).orElse("(none)"),
                linked,
                entitlements.builtinFrameworks(),
                questionnaire.segments().size(),
                questionnaire.segments().stream().mapToInt(s -> s.questions() == null ? 0 : s.questions().size()).sum(),
                ndiSegments,
                ndiQuestions,
                cmmiSegments,
                cmmiQuestions
        );
    }

    private static String normalizeEmail(String email) {
        return email == null ? "" : email.trim().toLowerCase(Locale.ROOT);
    }

    private Set<Framework> loadBuiltinFrameworks(Long projectId) {
        Set<Framework> out = new LinkedHashSet<>();
        for (String value : loadFrameworkValues(projectId)) {
            Framework framework = toFramework(value);
            if (framework != null) {
                out.add(framework);
            }
        }
        return out;
    }

    private java.util.List<String> loadFrameworkValues(Long projectId) {
        try {
            return jdbcTemplate.queryForList(
                    """
                            select coalesce(nullif(f.name, ''), pf.framework_id::text)
                            from project_framework pf
                            left join framework f on f.id = pf.framework_id
                            where pf.project_id = ?
                            """,
                    String.class,
                    projectId
            );
        } catch (Exception ignored) {
            return java.util.List.of();
        }
    }

    private static Framework toFramework(String raw) {
        if (raw == null) {
            return null;
        }
        String v = raw.trim().toUpperCase(Locale.ROOT);
        if (v.contains("NDI") || "1".equals(v)) {
            return Framework.NDI;
        }
        if (v.contains("CMMI") || "2".equals(v)) {
            return Framework.CMMI;
        }
        return null;
    }
}

