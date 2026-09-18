package org.example.pfebackend.staff;

import org.example.pfebackend.assessment.Assessment;
import org.example.pfebackend.assessment.AssessmentStatus;
import org.example.pfebackend.assessment.MaturityFrameworkDefinitionRepository;
import org.example.pfebackend.project.Framework;
import org.example.pfebackend.project.Project;
import org.example.pfebackend.project.ProjectRepository;
import org.example.pfebackend.staff.dto.AddProjectFrameworksRequest;
import org.example.pfebackend.staff.dto.AddClientRequest;
import org.example.pfebackend.staff.dto.AddProjectConsultantRequest;
import org.example.pfebackend.staff.dto.AssignConsultantRequest;
import org.example.pfebackend.staff.dto.CreateConsultantRequest;
import org.example.pfebackend.staff.dto.CreateManagerRequest;
import org.example.pfebackend.staff.dto.CreateProjectRequest;
import org.example.pfebackend.staff.dto.UpdateManagerParentRequest;
import org.example.pfebackend.user.AppUser;
import org.example.pfebackend.user.AppUserRepository;
import org.example.pfebackend.user.CommittedAppUserLoader;
import org.example.pfebackend.user.Role;
import org.springframework.dao.DataIntegrityViolationException;
import org.springframework.http.HttpStatus;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.web.server.ResponseStatusException;

import java.security.SecureRandom;
import java.util.EnumSet;
import java.util.HashSet;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.Objects;
import java.util.Set;

@Service
public class StaffService {

    private static final String DUPLICATE_NAME_MESSAGE = "Ce nom existe déjà dans la base de données.";

    private record ProjectRef(Long id, String name, Long clientId, String clientEmail) {}

    private final AppUserRepository appUserRepository;
    private final CommittedAppUserLoader committedAppUserLoader;
    private final PasswordEncoder passwordEncoder;
    private final ProjectRepository projectRepository;
    private final MaturityFrameworkDefinitionRepository maturityFrameworkDefinitionRepository;
    private final JdbcTemplate jdbcTemplate;
    private final SecureRandom secureRandom = new SecureRandom();

    public StaffService(
            AppUserRepository appUserRepository,
            CommittedAppUserLoader committedAppUserLoader,
            PasswordEncoder passwordEncoder,
            ProjectRepository projectRepository,
            MaturityFrameworkDefinitionRepository maturityFrameworkDefinitionRepository,
            JdbcTemplate jdbcTemplate
    ) {
        this.appUserRepository = appUserRepository;
        this.committedAppUserLoader = committedAppUserLoader;
        this.passwordEncoder = passwordEncoder;
        this.projectRepository = projectRepository;
        this.maturityFrameworkDefinitionRepository = maturityFrameworkDefinitionRepository;
        this.jdbcTemplate = jdbcTemplate;
    }

    public AppUser requireStaffByEmail(String email) {
        AppUser u = committedAppUserLoader.findByEmailInNewTransaction(normalizeEmail(email))
                .orElseThrow(() -> new ResponseStatusException(HttpStatus.UNAUTHORIZED, "User not found"));
        if (!isStaff(u.getRole())) {
            throw new ResponseStatusException(HttpStatus.FORBIDDEN, "Staff access only");
        }
        return u;
    }

    public static boolean isStaff(Role role) {
        return role == Role.ADMIN || role == Role.MANAGER || role == Role.CONSULTANT;
    }

    @Transactional(readOnly = true)
    public List<Map<String, Object>> listClientsWithSubmittedAssessments(AppUser viewer) {
        if (viewer.getRole() != Role.ADMIN && viewer.getRole() != Role.MANAGER && viewer.getRole() != Role.CONSULTANT) {
            throw new ResponseStatusException(HttpStatus.FORBIDDEN, "Not allowed");
        }
        List<AppUser> clients = appUserRepository.findDistinctClientsHavingAssessmentWithStatus(AssessmentStatus.SUBMITTED);
        if (viewer.getRole() == Role.CONSULTANT) {
            clients = clients.stream()
                    .filter(c -> consultantCanAccessClient(viewer.getId(), c.getId()))
                    .toList();
        }
        return clients.stream().map(this::toClientSummary).toList();
    }

    @Transactional(readOnly = true)
    public List<Map<String, Object>> listAllClients(AppUser actor) {
        if (actor.getRole() == Role.CONSULTANT) {
            return appUserRepository.findClientsAssignedToProjectConsultant(actor.getId()).stream()
                    .map(this::toClientSummary)
                    .toList();
        }
        if (actor.getRole() == Role.MANAGER) {
            return appUserRepository.findByRole(Role.CLIENT).stream()
                    .filter(c -> managerCanAccessClient(actor.getId(), c.getId()))
                    .map(this::toClientSummary)
                    .toList();
        }
        if (actor.getRole() != Role.ADMIN && actor.getRole() != Role.MANAGER) {
            throw new ResponseStatusException(HttpStatus.FORBIDDEN, "Only an admin or manager can list all clients");
        }
        return appUserRepository.findByRole(Role.CLIENT).stream()
                .map(this::toClientSummary)
                .toList();
    }

    @Transactional(readOnly = true)
    public List<Map<String, Object>> listProjectScopedClients(AppUser actor) {
        if (actor.getRole() == Role.ADMIN) {
            return appUserRepository.findByRole(Role.CLIENT).stream()
                    .map(this::toClientSummary)
                    .toList();
        }
        if (actor.getRole() == Role.MANAGER) {
            return appUserRepository.findByRole(Role.CLIENT).stream()
                    .filter(c -> managerCanAccessClient(actor.getId(), c.getId()))
                    .map(this::toClientSummary)
                    .toList();
        }
        throw new ResponseStatusException(HttpStatus.FORBIDDEN, "Only an admin or manager can list project clients");
    }

    @Transactional(readOnly = true)
    public void assertCanAccessClientData(AppUser staff, AppUser client) {
        if (client.getRole() != Role.CLIENT) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "Not a client");
        }
        if (staff.getRole() == Role.ADMIN) {
            return;
        }
        if (staff.getRole() == Role.MANAGER && managerCanAccessClient(staff.getId(), client.getId())) {
            return;
        }
        if (staff.getRole() == Role.CONSULTANT) {
            if (consultantCanAccessClient(staff.getId(), client.getId())) {
                return;
            }
        }
        throw new ResponseStatusException(HttpStatus.FORBIDDEN, "Not allowed to view this client");
    }

    @Transactional(readOnly = true)
    public void assertCanAccessAssessment(AppUser staff, Assessment assessment) {
        assertCanAccessClientData(staff, assessment.getClient());
    }

    @Transactional(readOnly = true)
    public void assertCanViewAssessmentVersions(AppUser staff, AppUser client) {
        if (staff.getRole() == Role.ADMIN) {
            throw new ResponseStatusException(HttpStatus.FORBIDDEN, "Admins cannot view assessment versions");
        }
        assertCanAccessClientData(staff, client);
    }

    @Transactional(readOnly = true)
    public void assertCanEditAssessment(AppUser staff, Assessment assessment) {
        AppUser client = assessment.getClient();
        if (client.getRole() != Role.CLIENT) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "Not a client");
        }
        if (staff.getRole() == Role.ADMIN) {
            return;
        }
        if (staff.getRole() == Role.CONSULTANT && consultantCanAccessClient(staff.getId(), client.getId())) {
            return;
        }
        if (staff.getRole() == Role.MANAGER && managerCanAccessClient(staff.getId(), client.getId())) {
            return;
        }
        throw new ResponseStatusException(HttpStatus.FORBIDDEN, "Not allowed to edit this client");
    }

    @Transactional
    public AppUser createManager(AppUser actor, CreateManagerRequest request) {
        if (actor.getRole() != Role.ADMIN) {
            throw new ResponseStatusException(HttpStatus.FORBIDDEN, "Only an admin can create a manager");
        }
        String email = normalizeEmail(request.email());
        if (appUserRepository.existsByEmailIgnoreCase(email)) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "Email is already used");
        }
        String fullName = normalizeName(request.fullName());
        assertUniqueFullName(fullName);
        AppUser parentManager = null;
        if (request.managerId() != null) {
            parentManager = requireManager(request.managerId());
        }
        AppUser m = new AppUser();
        m.setFullName(fullName);
        m.setEmail(email);
        m.setPassword(passwordEncoder.encode(request.password()));
        m.setRole(Role.MANAGER);
        m.setManagedBy(parentManager);
        return saveUserHandlingDuplicateName(m);
    }

    @Transactional
    public AppUser createConsultant(AppUser actor, CreateConsultantRequest request) {
        String email = normalizeEmail(request.email());
        if (appUserRepository.existsByEmailIgnoreCase(email)) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "Email is already used");
        }
        String fullName = normalizeName(request.fullName());
        assertUniqueFullName(fullName);

        AppUser manager;
        if (actor.getRole() == Role.MANAGER) {
            manager = actor;
        } else if (actor.getRole() == Role.ADMIN) {
            if (request.managerId() == null) {
                throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "managerId is required when an admin creates a consultant");
            }
            manager = appUserRepository.findById(request.managerId())
                    .orElseThrow(() -> new ResponseStatusException(HttpStatus.NOT_FOUND, "Manager not found"));
            if (manager.getRole() != Role.MANAGER) {
                throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "User is not a manager");
            }
        } else {
            throw new ResponseStatusException(HttpStatus.FORBIDDEN, "Only admin or manager can create a consultant");
        }

        AppUser c = new AppUser();
        c.setFullName(fullName);
        c.setEmail(email);
        c.setPassword(passwordEncoder.encode(request.password()));
        c.setRole(Role.CONSULTANT);
        c.setManagedBy(manager);
        return saveUserHandlingDuplicateName(c);
    }

    @Transactional
    public void deleteConsultant(AppUser actor, Long consultantId) {
        AppUser consultant = appUserRepository.findById(consultantId)
                .orElseThrow(() -> new ResponseStatusException(HttpStatus.NOT_FOUND, "User not found"));
        if (consultant.getRole() != Role.CONSULTANT) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "Not a consultant");
        }
        if (actor.getRole() == Role.MANAGER) {
            if (consultant.getManagedBy() == null || !Objects.equals(consultant.getManagedBy().getId(), actor.getId())) {
                throw new ResponseStatusException(HttpStatus.FORBIDDEN, "You can only remove consultants in your team");
            }
        } else if (actor.getRole() != Role.ADMIN) {
            throw new ResponseStatusException(HttpStatus.FORBIDDEN, "Not allowed");
        }

        jdbcTemplate.update("delete from project_consultants where consultant_id = ?", consultantId);
        appUserRepository.delete(consultant);
    }

    @Transactional
    public Map<String, Object> updateManagerParent(AppUser actor, Long managerId, UpdateManagerParentRequest request) {
        if (actor.getRole() != Role.ADMIN) {
            throw new ResponseStatusException(HttpStatus.FORBIDDEN, "Only an admin can update manager hierarchy");
        }

        AppUser manager = requireManager(managerId);
        AppUser parentManager = null;
        Long parentManagerId = request.managerId();
        if (parentManagerId != null) {
            if (Objects.equals(manager.getId(), parentManagerId)) {
                throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "A manager cannot be their own superior manager");
            }
            parentManager = requireManager(parentManagerId);
            if (parentManager.getManagedBy() != null) {
                throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "Only top-level managers can be selected");
            }
            if (!appUserRepository.findByRoleAndManagedBy_Id(Role.MANAGER, manager.getId()).isEmpty()) {
                throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "A manager with subordinate managers cannot be assigned under another manager");
            }
            assertNoManagerHierarchyCycle(manager.getId(), parentManager);
        }

        manager.setManagedBy(parentManager);
        return toStaffSummary(saveUserAndFlushHandlingDuplicateName(manager));
    }

    @Transactional(readOnly = true)
    public List<Map<String, Object>> listManagers(AppUser actor) {
        if (actor.getRole() == Role.ADMIN) {
            return appUserRepository.findByRole(Role.MANAGER).stream().map(this::toStaffSummary).toList();
        }
        if (actor.getRole() == Role.MANAGER) {
            return appUserRepository.findByRoleAndManagedBy_Id(Role.MANAGER, actor.getId()).stream()
                    .map(this::toStaffSummary)
                    .toList();
        }
        throw new ResponseStatusException(HttpStatus.FORBIDDEN, "Not allowed");
    }

    @Transactional(readOnly = true)
    public List<Map<String, Object>> listConsultants(AppUser actor, Long managerIdFilter) {
        if (actor.getRole() == Role.ADMIN) {
            if (managerIdFilter != null) {
                return appUserRepository.findByRoleAndManagedBy_Id(Role.CONSULTANT, managerIdFilter).stream()
                        .map(this::toConsultantSummary)
                        .toList();
            }
            return appUserRepository.findByRole(Role.CONSULTANT).stream().map(this::toConsultantSummary).toList();
        }
        if (actor.getRole() == Role.MANAGER) {
            return appUserRepository.findByRoleAndManagedBy_Id(Role.CONSULTANT, actor.getId()).stream()
                    .map(this::toConsultantSummary)
                    .toList();
        }
        throw new ResponseStatusException(HttpStatus.FORBIDDEN, "Not allowed");
    }

    @Transactional
    public void assignConsultantToClient(AppUser actor, Long clientId, AssignConsultantRequest request) {
        if (actor.getRole() != Role.ADMIN && actor.getRole() != Role.MANAGER) {
            throw new ResponseStatusException(HttpStatus.FORBIDDEN, "Only admin or manager can assign a consultant to a client");
        }
        AppUser client = appUserRepository.findById(clientId)
                .orElseThrow(() -> new ResponseStatusException(HttpStatus.NOT_FOUND, "Client not found"));
        if (client.getRole() != Role.CLIENT) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "Not a client");
        }
        AppUser consultant = requireAllowedProjectAssignee(actor, request.consultantId());
        ProjectRef project = latestProjectForClient(client);
        addConsultantToProjectIfMissing(project.id(), consultant.getId(), false);
    }

    @Transactional
    public Map<String, Object> addNewClient(AppUser actor, AddClientRequest request) {
        if (actor.getRole() != Role.ADMIN) {
            throw new ResponseStatusException(HttpStatus.FORBIDDEN, "Only an admin can add a client");
        }
        String email = normalizeEmail(request.email());
        if (appUserRepository.existsByEmailIgnoreCase(email)) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "Email is already used");
        }
        String fullName = normalizeName((request.firstName().trim() + " " + request.lastName().trim()).trim());
        assertUniqueFullName(fullName);

        String rawPassword = generatePassword();

        AppUser c = new AppUser();
        c.setFullName(fullName);
        c.setEmail(email);
        c.setPassword(passwordEncoder.encode(rawPassword));
        c.setRole(Role.CLIENT);
        c.setManagedBy(null);
        // Force INSERT to the DB before this transaction completes so the next request (login) always sees the row.
        AppUser saved = saveUserAndFlushHandlingDuplicateName(c);

        return Map.of(
                "id", saved.getId(),
                "email", saved.getEmail(),
                "fullName", saved.getFullName(),
                "generatedPassword", rawPassword
        );
    }

    @Transactional
    public Map<String, Object> resetClientPassword(AppUser actor, Long clientId) {
        if (actor.getRole() != Role.ADMIN) {
            throw new ResponseStatusException(HttpStatus.FORBIDDEN, "Only an admin can reset a client password");
        }
        AppUser client = appUserRepository.findById(clientId)
                .orElseThrow(() -> new ResponseStatusException(HttpStatus.NOT_FOUND, "Client not found"));
        if (client.getRole() != Role.CLIENT) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "Not a client");
        }

        String rawPassword = generatePassword();
        client.setPassword(passwordEncoder.encode(rawPassword));
        AppUser saved = appUserRepository.saveAndFlush(client);

        return Map.of(
                "id", saved.getId(),
                "email", saved.getEmail(),
                "fullName", saved.getFullName(),
                "generatedPassword", rawPassword
        );
    }

    @Transactional
    public Map<String, Object> createNewProject(AppUser actor, CreateProjectRequest request) {
        if (actor.getRole() != Role.ADMIN && actor.getRole() != Role.MANAGER) {
            throw new ResponseStatusException(HttpStatus.FORBIDDEN, "Only an admin or manager can create a project");
        }
        AppUser client = appUserRepository.findById(request.clientId())
                .orElseThrow(() -> new ResponseStatusException(HttpStatus.NOT_FOUND, "Client not found"));
        if (client.getRole() != Role.CLIENT) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "Not a client");
        }
        if (actor.getRole() == Role.MANAGER) {
            assertCanManageProject(actor, client);
        }
        Set<Framework> frameworks = request.frameworks() == null ? Set.of() : new HashSet<>(request.frameworks());
        Set<Long> customFwIds = request.customMaturityFrameworkIds() == null ? Set.of() : new HashSet<>(request.customMaturityFrameworkIds());
        if (frameworks.isEmpty() && customFwIds.isEmpty()) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "Assign at least one built-in framework and/or custom maturity framework");
        }
        if (!customFwIds.isEmpty()) {
            long found = maturityFrameworkDefinitionRepository.countByIdIn(customFwIds);
            if (found != customFwIds.size()) {
                throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "One or more custom maturity framework ids are invalid");
            }
        }

        Project p = new Project();
        p.setClient(client);
        String name = request.name() == null ? "" : request.name().trim();
        if (name.isBlank()) {
            name = "Project - " + client.getFullName();
        }
        p.setName(name);
        p.setFrameworks(frameworks);
        p.setCustomMaturityFrameworkIds(customFwIds);
        Project saved = projectRepository.saveAndFlush(p);
        addBuiltinFrameworks(saved.getId(), frameworks);
        if (request.consultantId() != null) {
            AppUser assignee = requireAllowedProjectAssignee(actor, request.consultantId());
            addConsultantToProjectIfMissing(saved.getId(), assignee.getId(), Boolean.TRUE.equals(request.canManageProject()));
        }

        return toProjectSummary(saved);
    }

    @Transactional
    public Map<String, Object> addFrameworksToProject(AppUser actor, Long projectId, AddProjectFrameworksRequest request) {
        Project project = projectRepository.findById(projectId)
                .orElseThrow(() -> new ResponseStatusException(HttpStatus.NOT_FOUND, "Project not found"));
        assertCanManageScopedProject(actor, project.getClient());
        return addFrameworksToProject(project, request);
    }

    @Transactional
    public Map<String, Object> addFrameworksToLatestClientProject(AppUser actor, Long clientId, AddProjectFrameworksRequest request) {
        AppUser client = appUserRepository.findById(clientId)
                .orElseThrow(() -> new ResponseStatusException(HttpStatus.NOT_FOUND, "Client not found"));
        if (client.getRole() != Role.CLIENT) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "Not a client");
        }
        assertCanManageScopedProject(actor, client);
        ProjectRef project = latestProjectForClient(client);
        return addFrameworksToProject(project, request);
    }

    @Transactional(readOnly = true)
    public List<Map<String, Object>> listFrameworksForLatestClientProject(AppUser actor, Long clientId) {
        AppUser client = appUserRepository.findById(clientId)
                .orElseThrow(() -> new ResponseStatusException(HttpStatus.NOT_FOUND, "Client not found"));
        assertCanAccessClientData(actor, client);
        List<Map<String, Object>> frameworks = loadFrameworkSummariesForClient(client.getId());
        if (!frameworks.isEmpty()) {
            return frameworks;
        }
        return List.of();
    }

    @Transactional
    public Map<String, Object> getProjectSummary(AppUser actor, Long projectId) {
        Project project = projectRepository.findById(projectId)
                .orElseThrow(() -> new ResponseStatusException(HttpStatus.NOT_FOUND, "Project not found"));
        assertCanAccessClientData(actor, project.getClient());
        return toProjectSummary(project);
    }

    @Transactional
    public Map<String, Object> getLatestClientProjectSummary(AppUser actor, Long clientId) {
        AppUser client = appUserRepository.findById(clientId)
                .orElseThrow(() -> new ResponseStatusException(HttpStatus.NOT_FOUND, "Client not found"));
        assertCanAccessClientData(actor, client);
        ProjectRef project = latestProjectForClient(client);
        return toProjectSummary(project);
    }

    @Transactional
    public List<Map<String, Object>> listProjectConsultants(AppUser actor, Long projectId) {
        Project project = projectRepository.findById(projectId)
                .orElseThrow(() -> new ResponseStatusException(HttpStatus.NOT_FOUND, "Project not found"));
        assertCanAccessClientData(actor, project.getClient());
        return loadProjectConsultants(projectId);
    }

    /**
     * Assigned staff for a project from {@code project_consultants}.
     * Shared by Existing Projects and assessment list summaries (no auth checks — caller is responsible).
     */
    @Transactional(readOnly = true)
    public List<Map<String, Object>> assignedStaffForProject(Long projectId) {
        if (projectId == null) {
            return List.of();
        }
        return loadProjectConsultants(projectId);
    }

    @Transactional
    public List<Map<String, Object>> listLatestClientProjectConsultants(AppUser actor, Long clientId) {
        AppUser client = appUserRepository.findById(clientId)
                .orElseThrow(() -> new ResponseStatusException(HttpStatus.NOT_FOUND, "Client not found"));
        assertCanManageProjectConsultants(actor, client);
        ProjectRef project = latestProjectForClient(client);
        return loadProjectConsultants(project.id());
    }

    @Transactional
    public List<Map<String, Object>> listAvailableProjectConsultants(AppUser actor, Long projectId) {
        Project project = projectRepository.findById(projectId)
                .orElseThrow(() -> new ResponseStatusException(HttpStatus.NOT_FOUND, "Project not found"));
        assertCanManageProjectConsultants(actor, project.getClient());
        return loadAllAvailableProjectAssignees(projectId);
    }

    @Transactional
    public List<Map<String, Object>> listAvailableLatestClientProjectConsultants(AppUser actor, Long clientId) {
        AppUser client = appUserRepository.findById(clientId)
                .orElseThrow(() -> new ResponseStatusException(HttpStatus.NOT_FOUND, "Client not found"));
        assertCanManageProjectConsultants(actor, client);
        ProjectRef project = latestProjectForClient(client);
        return loadAllAvailableProjectAssignees(project.id());
    }

    @Transactional
    public Map<String, Object> addConsultantToProject(AppUser actor, Long projectId, AddProjectConsultantRequest request) {
        Project project = projectRepository.findById(projectId)
                .orElseThrow(() -> new ResponseStatusException(HttpStatus.NOT_FOUND, "Project not found"));
        assertCanManageProjectConsultants(actor, project.getClient());
        AppUser consultant = requireAllowedProjectAssignee(actor, request.consultantId());
        if (isConsultantAssignedToProject(projectId, consultant.getId())) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "Consultant is already associated with this project");
        }
        addConsultantToProjectIfMissing(projectId, consultant.getId(), Boolean.TRUE.equals(request.canManageProject()));
        return projectConsultantSummary(actor, projectId);
    }

    @Transactional
    public Map<String, Object> addConsultantToLatestClientProject(AppUser actor, Long clientId, AddProjectConsultantRequest request) {
        AppUser client = appUserRepository.findById(clientId)
                .orElseThrow(() -> new ResponseStatusException(HttpStatus.NOT_FOUND, "Client not found"));
        assertCanManageProjectConsultants(actor, client);
        ProjectRef project = latestProjectForClient(client);
        AppUser consultant = requireAllowedProjectAssignee(actor, request.consultantId());
        if (isConsultantAssignedToProject(project.id(), consultant.getId())) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "Consultant is already associated with this project");
        }
        addConsultantToProjectIfMissing(project.id(), consultant.getId(), Boolean.TRUE.equals(request.canManageProject()));
        return projectConsultantSummary(actor, project.id());
    }

    private Map<String, Object> addFrameworksToProject(Project project, AddProjectFrameworksRequest request) {
        return addFrameworksToProject(
                new ProjectRef(project.getId(), project.getName(), project.getClient().getId(), project.getClient().getEmail()),
                project.getCustomMaturityFrameworkIds(),
                request
        );
    }

    private Map<String, Object> addFrameworksToProject(ProjectRef project, AddProjectFrameworksRequest request) {
        return addFrameworksToProject(project, Set.of(), request);
    }

    private Map<String, Object> addFrameworksToProject(
            ProjectRef project,
            Set<Long> existingCustomFrameworkIds,
            AddProjectFrameworksRequest request
    ) {
        Set<Framework> frameworksToAdd = request == null || request.frameworks() == null
                ? new HashSet<>()
                : new HashSet<>(request.frameworks());
        if (request != null && request.framework() != null) {
            frameworksToAdd.add(request.framework());
        }
        Set<Framework> existingBuiltinFrameworks = loadBuiltinFrameworks(project.id());
        Set<Long> customFrameworkIdsToAdd = request == null || request.customMaturityFrameworkIds() == null
                ? new HashSet<>()
                : new HashSet<>(request.customMaturityFrameworkIds());
        if (request != null && request.customMaturityFrameworkId() != null) {
            customFrameworkIdsToAdd.add(request.customMaturityFrameworkId());
        }
        if (frameworksToAdd.isEmpty() && customFrameworkIdsToAdd.isEmpty()) {
            Set<Framework> missingBuiltinFrameworks = EnumSet.allOf(Framework.class);
            missingBuiltinFrameworks.removeAll(existingBuiltinFrameworks);
            if (missingBuiltinFrameworks.size() == 1) {
                frameworksToAdd.add(missingBuiltinFrameworks.iterator().next());
            } else if (missingBuiltinFrameworks.isEmpty()) {
                return toProjectSummary(project);
            } else {
                throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "Select at least one framework to add");
            }
        }
        if (!customFrameworkIdsToAdd.isEmpty()) {
            long found = maturityFrameworkDefinitionRepository.countByIdIn(customFrameworkIdsToAdd);
            if (found != customFrameworkIdsToAdd.size()) {
                throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "One or more custom maturity framework ids are invalid");
            }
            Set<Long> existingFrameworkIds = loadFrameworkIds(project.id());
            customFrameworkIdsToAdd.removeAll(existingFrameworkIds);
        }
        frameworksToAdd.removeAll(existingBuiltinFrameworks);
        if (frameworksToAdd.isEmpty() && customFrameworkIdsToAdd.isEmpty()) {
            return toProjectSummary(project);
        }

        Set<Framework> mergedFrameworks = new HashSet<>(existingBuiltinFrameworks);
        mergedFrameworks.addAll(frameworksToAdd);
        addBuiltinFrameworks(project.id(), frameworksToAdd);
        addFrameworkIds(project.id(), customFrameworkIdsToAdd);

        Set<Long> mergedCustomFrameworkIds = new HashSet<>(existingCustomFrameworkIds == null ? Set.of() : existingCustomFrameworkIds);
        mergedCustomFrameworkIds.addAll(customFrameworkIdsToAdd);

        return toProjectSummary(project, mergedFrameworks, mergedCustomFrameworkIds);
    }

    private void assertCanManageProjectConsultants(AppUser actor, AppUser client) {
        if (actor.getRole() == Role.ADMIN) {
            return;
        }
        if (actor.getRole() == Role.MANAGER && managerCanAccessClient(actor.getId(), client.getId())) {
            return;
        }
        throw new ResponseStatusException(HttpStatus.FORBIDDEN, "Only an admin or an authorized project manager can manage this project");
    }

    private void assertCanManageProject(AppUser actor, AppUser client) {
        if (actor.getRole() == Role.ADMIN) {
            return;
        }
        if (actor.getRole() == Role.MANAGER && managerCanManageProjectForClient(actor.getId(), client.getId())) {
            return;
        }
        throw new ResponseStatusException(HttpStatus.FORBIDDEN, "Only an admin or an authorized project manager can manage this project");
    }

    private void assertCanManageScopedProject(AppUser actor, AppUser client) {
        if (actor.getRole() == Role.ADMIN) {
            return;
        }
        if (actor.getRole() == Role.MANAGER && managerCanAccessClient(actor.getId(), client.getId())) {
            return;
        }
        throw new ResponseStatusException(HttpStatus.FORBIDDEN, "Only an admin or an authorized project manager can manage this project");
    }

    private AppUser requireAllowedProjectAssignee(AppUser actor, Long assigneeId) {
        AppUser assignee = appUserRepository.findById(assigneeId)
                .orElseThrow(() -> new ResponseStatusException(HttpStatus.NOT_FOUND, "Project assignee not found"));
        if (assignee.getRole() != Role.CONSULTANT && assignee.getRole() != Role.MANAGER) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "User must be a consultant or manager");
        }
        if (actor.getRole() != Role.ADMIN && actor.getRole() != Role.MANAGER) {
            throw new ResponseStatusException(HttpStatus.FORBIDDEN, "Not allowed");
        }
        return assignee;
    }

    private boolean isConsultantAssignedToProject(Long projectId, Long consultantId) {
        Integer count = jdbcTemplate.queryForObject(
                "select count(*) from project_consultants where project_id = ? and consultant_id = ?",
                Integer.class,
                projectId,
                consultantId
        );
        return count != null && count > 0;
    }

    private void addConsultantToProjectIfMissing(Long projectId, Long consultantId, boolean canManageProject) {
        jdbcTemplate.update(
                """
                        insert into project_consultants(project_id, consultant_id, assigned_at, can_manage_project)
                        select ?, ?, now(), ?
                        where not exists (
                            select 1
                            from project_consultants
                            where project_id = ?
                              and consultant_id = ?
                        )
                        """,
                projectId,
                consultantId,
                canManageProject,
                projectId,
                consultantId
        );
    }

    private boolean consultantCanAccessClient(Long consultantId, Long clientId) {
        Integer count = jdbcTemplate.queryForObject(
                """
                        select count(*)
                        from project p
                        join project_consultants pc on pc.project_id = p.id
                        where p.client_id = ?
                          and pc.consultant_id = ?
                        """,
                Integer.class,
                clientId,
                consultantId
        );
        return count != null && count > 0;
    }

    private boolean managerCanAccessClient(Long managerId, Long clientId) {
        Integer count = jdbcTemplate.queryForObject(
                """
                        select count(*)
                        from project p
                        join project_consultants pc on pc.project_id = p.id
                        join app_user assignee on assignee.id = pc.consultant_id
                        where p.client_id = ?
                          and (
                              pc.consultant_id = ?
                              or assignee.managed_by_id = ?
                          )
                        """,
                Integer.class,
                clientId,
                managerId,
                managerId
        );
        return count != null && count > 0;
    }

    private boolean managerCanManageProjectForClient(Long managerId, Long clientId) {
        Integer count = jdbcTemplate.queryForObject(
                """
                        select count(*)
                        from project p
                        join project_consultants pc on pc.project_id = p.id
                        join app_user assignee on assignee.id = pc.consultant_id
                        where p.client_id = ?
                          and pc.can_manage_project = true
                          and (
                              pc.consultant_id = ?
                              or assignee.managed_by_id = ?
                          )
                        """,
                Integer.class,
                clientId,
                managerId,
                managerId
        );
        return count != null && count > 0;
    }

    private boolean latestProjectHasNoAssignees(Long clientId) {
        Integer count = jdbcTemplate.queryForObject(
                """
                        select count(*)
                        from project p
                        where p.client_id = ?
                          and p.id = (
                              select latest.id
                              from project latest
                              where latest.client_id = ?
                              order by latest.created_at desc nulls last, latest.id desc
                              limit 1
                          )
                          and not exists (
                              select 1
                              from project_consultants pc
                              where pc.project_id = p.id
                          )
                        """,
                Integer.class,
                clientId,
                clientId
        );
        return count != null && count > 0;
    }

    private List<Map<String, Object>> loadProjectConsultants(Long projectId) {
        return jdbcTemplate.query(
                """
                        select
                            u.id,
                            u.full_name,
                            u.email,
                            u.role,
                            u.created_at,
                            u.managed_by_id,
                            coalesce(pc.can_manage_project, false) as can_manage_project,
                            m.full_name as manager_name
                        from project_consultants pc
                        join app_user u on u.id = pc.consultant_id
                        left join app_user m on m.id = u.managed_by_id
                        where pc.project_id = ?
                        order by lower(coalesce(u.full_name, u.email)), u.id
                        """,
                (rs, rowNum) -> {
                    Map<String, Object> m = new java.util.LinkedHashMap<>();
                    java.sql.Timestamp createdAt = rs.getTimestamp("created_at");
                    m.put("id", rs.getLong("id"));
                    m.put("fullName", rs.getString("full_name"));
                    m.put("email", rs.getString("email"));
                    m.put("role", rs.getString("role"));
                    m.put("createdAt", createdAt == null ? null : createdAt.toInstant());
                    long managerId = rs.getLong("managed_by_id");
                    m.put("managerId", rs.wasNull() ? null : managerId);
                    m.put("managerName", rs.getString("manager_name"));
                    m.put("canManageProject", rs.getBoolean("can_manage_project"));
                    return m;
                },
                projectId
        );
    }

    private List<Map<String, Object>> loadLatestProjectConsultantsForClient(Long clientId) {
        try {
            List<Long> projectIds = jdbcTemplate.queryForList(
                    """
                            select id
                            from project
                            where client_id = ?
                            order by created_at desc nulls last, id desc
                            limit 1
                            """,
                    Long.class,
                    clientId
            );
            if (projectIds.isEmpty()) {
                return List.of();
            }
            return loadProjectConsultants(projectIds.get(0));
        } catch (Exception ignored) {
            return List.of();
        }
    }

    private List<Map<String, Object>> loadAllAvailableProjectAssignees(Long projectId) {
        return appUserRepository.findAvailableProjectAssignees(List.of(Role.CONSULTANT, Role.MANAGER), projectId).stream()
                .map(this::toConsultantSummary)
                .toList();
    }

    private Map<String, Object> projectConsultantSummary(AppUser actor, Long projectId) {
        Map<String, Object> out = new java.util.LinkedHashMap<>();
        List<Map<String, Object>> projectConsultants = loadProjectConsultants(projectId);
        out.put("projectId", projectId);
        out.put("consultants", projectConsultants);
        out.put("projectConsultants", projectConsultants);
        out.put("availableConsultants", loadAllAvailableProjectAssignees(projectId));
        return out;
    }

    private String generatePassword() {
        // 12 chars, avoids ambiguous characters
        final String alphabet = "ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz23456789@#$%";
        StringBuilder sb = new StringBuilder(12);
        for (int i = 0; i < 12; i++) {
            sb.append(alphabet.charAt(secureRandom.nextInt(alphabet.length())));
        }
        return sb.toString();
    }

    private String normalizeName(String value) {
        String name = value == null ? "" : value.trim().replaceAll("\\s+", " ");
        if (name.isBlank()) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "Name is required");
        }
        return name;
    }

    private void assertUniqueFullName(String fullName) {
        if (appUserRepository.existsByFullNameIgnoreCase(fullName)) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, DUPLICATE_NAME_MESSAGE);
        }
    }

    private AppUser saveUserHandlingDuplicateName(AppUser user) {
        try {
            return appUserRepository.save(user);
        } catch (DataIntegrityViolationException e) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, DUPLICATE_NAME_MESSAGE);
        }
    }

    private AppUser saveUserAndFlushHandlingDuplicateName(AppUser user) {
        try {
            return appUserRepository.saveAndFlush(user);
        } catch (DataIntegrityViolationException e) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, DUPLICATE_NAME_MESSAGE);
        }
    }

    private AppUser requireManager(Long managerId) {
        AppUser manager = appUserRepository.findById(managerId)
                .orElseThrow(() -> new ResponseStatusException(HttpStatus.NOT_FOUND, "Manager not found"));
        if (manager.getRole() != Role.MANAGER) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "User is not a manager");
        }
        return manager;
    }

    private void assertNoManagerHierarchyCycle(Long managerId, AppUser parentManager) {
        Set<Long> visited = new HashSet<>();
        AppUser current = parentManager;
        while (current != null) {
            Long currentId = current.getId();
            if (Objects.equals(currentId, managerId)) {
                throw new ResponseStatusException(
                        HttpStatus.BAD_REQUEST,
                        "A manager cannot be assigned under one of their subordinate managers"
                );
            }
            if (currentId == null || !visited.add(currentId)) {
                throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "Manager hierarchy already contains a loop");
            }
            current = current.getManagedBy();
        }
    }

    private boolean isManagedBy(AppUser user, Long managerId) {
        return user.getManagedBy() != null && Objects.equals(user.getManagedBy().getId(), managerId);
    }

    private Map<String, Object> toClientSummary(AppUser c) {
        Map<String, Object> m = new java.util.LinkedHashMap<>();
        List<Map<String, Object>> projectConsultants = loadLatestProjectConsultantsForClient(c.getId());
        m.put("id", c.getId());
        m.put("fullName", c.getFullName());
        m.put("email", c.getEmail());
        m.put("createdAt", c.getCreatedAt());
        m.put("projectConsultants", projectConsultants);
        m.put(
                "projectConsultantNames",
                projectConsultants.stream()
                        .map(row -> row.get("fullName") != null ? row.get("fullName") : row.get("email"))
                        .filter(Objects::nonNull)
                        .map(String::valueOf)
                        .toList()
        );
        return m;
    }

    private Map<String, Object> toStaffSummary(AppUser u) {
        Map<String, Object> m = new java.util.LinkedHashMap<>();
        m.put("id", u.getId());
        m.put("fullName", u.getFullName());
        m.put("email", u.getEmail());
        m.put("role", u.getRole());
        m.put("createdAt", u.getCreatedAt());
        m.put("managerId", u.getManagedBy() != null ? u.getManagedBy().getId() : null);
        m.put("managerName", u.getManagedBy() != null ? u.getManagedBy().getFullName() : null);
        return m;
    }

    private Map<String, Object> toConsultantSummary(AppUser u) {
        Map<String, Object> m = new java.util.LinkedHashMap<>();
        m.put("id", u.getId());
        m.put("fullName", u.getFullName());
        m.put("email", u.getEmail());
        m.put("role", u.getRole());
        m.put("createdAt", u.getCreatedAt());
        m.put("managerId", u.getManagedBy() != null ? u.getManagedBy().getId() : null);
        m.put("managerName", u.getManagedBy() != null ? u.getManagedBy().getFullName() : null);
        return m;
    }

    private Map<String, Object> toProjectSummary(Project project) {
        Map<String, Object> out = new java.util.LinkedHashMap<>();
        out.put("id", project.getId());
        out.put("name", project.getName());
        out.put("clientId", project.getClient().getId());
        out.put("clientEmail", project.getClient().getEmail());
        out.put("frameworks", loadBuiltinFrameworks(project.getId()));
        out.put("customMaturityFrameworkIds", project.getCustomMaturityFrameworkIds());
        List<Map<String, Object>> projectConsultants = loadProjectConsultants(project.getId());
        out.put("consultants", projectConsultants);
        out.put("projectConsultants", projectConsultants);
        addProjectAssignmentSummary(out, projectConsultants);
        addProjectStatusSummary(out, project.getId(), project.getClient().getId());
        return out;
    }

    private Map<String, Object> toProjectSummary(ProjectRef project) {
        return toProjectSummary(project, loadBuiltinFrameworks(project.id()), Set.of());
    }

    private Map<String, Object> toProjectSummary(ProjectRef project, Set<Framework> frameworks, Set<Long> customFrameworkIds) {
        Map<String, Object> out = new java.util.LinkedHashMap<>();
        out.put("id", project.id());
        out.put("name", project.name());
        out.put("clientId", project.clientId());
        out.put("clientEmail", project.clientEmail());
        out.put("frameworks", frameworks);
        out.put("customMaturityFrameworkIds", customFrameworkIds);
        List<Map<String, Object>> projectConsultants = loadProjectConsultants(project.id());
        out.put("consultants", projectConsultants);
        out.put("projectConsultants", projectConsultants);
        addProjectAssignmentSummary(out, projectConsultants);
        addProjectStatusSummary(out, project.id(), project.clientId());
        return out;
    }

    private void addProjectAssignmentSummary(Map<String, Object> out, List<Map<String, Object>> projectConsultants) {
        List<String> names = projectConsultants.stream()
                .map(row -> row.get("fullName") != null ? row.get("fullName") : row.get("email"))
                .filter(Objects::nonNull)
                .map(String::valueOf)
                .toList();
        String label = names.isEmpty() ? null : String.join(", ", names);
        out.put("assignedStaffNames", names);
        out.put("projectConsultantNames", names);
        out.put("assignedStaff", label);
        out.put("assignedConsultantName", label);
        out.put("consultantName", label);
    }

    private void addProjectStatusSummary(Map<String, Object> out, Long projectId, Long clientId) {
        String status = latestAssessmentStatusForProject(projectId, clientId);
        out.put("status", status);
        out.put("projectStatus", status);
        out.put("workflowStatus", status);
        out.put("assessmentStatus", status);
    }

    private String latestAssessmentStatusForProject(Long projectId, Long clientId) {
        List<String> statuses = jdbcTemplate.queryForList(
                """
                        select status
                        from assessment
                        where project_id = ?
                        order by year desc nulls last, version desc, created_at desc nulls last, id desc
                        limit 1
                        """,
                String.class,
                projectId
        );
        if (statuses.isEmpty() && clientId != null) {
            statuses = jdbcTemplate.queryForList(
                    """
                            select status
                            from assessment
                            where client_id = ?
                            order by year desc nulls last, version desc, created_at desc nulls last, id desc
                            limit 1
                            """,
                    String.class,
                    clientId
            );
        }
        if (statuses.isEmpty() || statuses.get(0) == null || statuses.get(0).isBlank()) {
            return "No assessment";
        }
        return switch (statuses.get(0).toUpperCase(Locale.ROOT)) {
            case "SUBMITTED" -> "Submitted";
            case "DRAFT", "IN_PROGRESS" -> "Current Assessment";
            default -> statuses.get(0);
        };
    }

    private ProjectRef latestProjectForClient(AppUser client) {
        List<ProjectRef> byCreatedAt = queryLatestProject(client, "created_at desc nulls last, id desc");
        if (!byCreatedAt.isEmpty()) {
            return byCreatedAt.get(0);
        }
        List<ProjectRef> byId = queryLatestProject(client, "id desc");
        if (byId.isEmpty()) {
            throw new ResponseStatusException(HttpStatus.NOT_FOUND, "Project not found for client");
        }
        return byId.get(0);
    }

    private List<ProjectRef> queryLatestProject(AppUser client, String orderBy) {
        try {
            return jdbcTemplate.query(
                    ("""
                            select id, name
                            from project
                            where client_id = ?
                            order by %s
                            limit 1
                            """).formatted(orderBy),
                    (rs, rowNum) -> new ProjectRef(
                            rs.getLong("id"),
                            rs.getString("name"),
                            client.getId(),
                            client.getEmail()
                    ),
                    client.getId()
            );
        } catch (Exception ignored) {
            return List.of();
        }
    }

    private List<Map<String, Object>> loadFrameworkSummaries(Long projectId) {
        try {
            return jdbcTemplate.query(
                    """
                            select
                                pf.framework_id as id,
                                case
                                    when pf.framework_id = 1 or upper(coalesce(f.name, '')) like '%NDI%' then 'NDI'
                                    when pf.framework_id = 2 or upper(coalesce(f.name, '')) like '%CMMI%' then 'CMMI'
                                    else coalesce(upper(nullif(f.name, '')), cast(pf.framework_id as varchar))
                                end as code,
                                coalesce(
                                    nullif(f.name, ''),
                                    case
                                        when pf.framework_id = 1 then 'NDI'
                                        when pf.framework_id = 2 then 'CMMI'
                                        else cast(pf.framework_id as varchar)
                                    end
                                ) as name
                            from project_framework pf
                            left join framework f on f.id = pf.framework_id
                            where pf.project_id = ?
                            order by pf.framework_id
                            """,
                    (rs, rowNum) -> {
                        Map<String, Object> m = new java.util.LinkedHashMap<>();
                        String rawCode = rs.getString("code");
                        String name = rs.getString("name");
                        Framework builtin = toFramework(rawCode);
                        if (builtin == null) {
                            builtin = toFramework(name);
                        }
                        m.put("id", rs.getLong("id"));
                        m.put("code", builtin == null ? rawCode : builtin.name());
                        m.put("name", name);
                        return m;
                    },
                    projectId
            );
        } catch (Exception ignored) {
            return List.of();
        }
    }

    private List<Map<String, Object>> loadFrameworkSummariesForClient(Long clientId) {
        try {
            return jdbcTemplate.query(
                    """
                            select
                                pf.framework_id as id,
                                max(
                                    case
                                        when pf.framework_id = 1 or upper(coalesce(f.name, '')) like '%NDI%' then 'NDI'
                                        when pf.framework_id = 2 or upper(coalesce(f.name, '')) like '%CMMI%' then 'CMMI'
                                        else coalesce(upper(nullif(f.name, '')), cast(pf.framework_id as varchar))
                                    end
                                ) as code,
                                max(
                                    coalesce(
                                        nullif(f.name, ''),
                                        case
                                            when pf.framework_id = 1 then 'NDI'
                                            when pf.framework_id = 2 then 'CMMI'
                                            else cast(pf.framework_id as varchar)
                                        end
                                    )
                                ) as name
                            from project p
                            join project_framework pf on pf.project_id = p.id
                            left join framework f on f.id = pf.framework_id
                            where p.client_id = ?
                            group by pf.framework_id
                            order by pf.framework_id
                            """,
                    (rs, rowNum) -> {
                        Map<String, Object> m = new java.util.LinkedHashMap<>();
                        String rawCode = rs.getString("code");
                        String name = rs.getString("name");
                        Framework builtin = toFramework(rawCode);
                        if (builtin == null) {
                            builtin = toFramework(name);
                        }
                        m.put("id", rs.getLong("id"));
                        m.put("code", builtin == null ? rawCode : builtin.name());
                        m.put("name", name);
                        return m;
                    },
                    clientId
            );
        } catch (Exception ignored) {
            return List.of();
        }
    }

    private Set<Long> loadFrameworkIds(Long projectId) {
        try {
            return new LinkedHashSet<>(jdbcTemplate.queryForList(
                    "select framework_id from project_framework where project_id = ?",
                    Long.class,
                    projectId
            ));
        } catch (Exception ignored) {
            return Set.of();
        }
    }

    private void addFrameworkIds(Long projectId, Set<Long> frameworkIds) {
        for (Long frameworkId : frameworkIds) {
            insertProjectFramework(projectId, frameworkId);
        }
    }

    private void insertProjectFramework(Long projectId, Long frameworkId) {
        try {
            jdbcTemplate.update(
                    "insert into project_framework(project_id, framework_id) values (?, ?)",
                    projectId,
                    frameworkId
            );
        } catch (Exception ignored) {
            throw new ResponseStatusException(HttpStatus.INTERNAL_SERVER_ERROR, "Could not assign framework to project");
        }
    }

    private void addBuiltinFrameworks(Long projectId, Set<Framework> frameworks) {
        for (Framework framework : frameworks) {
            Long frameworkId = resolveFrameworkId(framework);
            if (frameworkId == null) {
                throw new ResponseStatusException(HttpStatus.INTERNAL_SERVER_ERROR, "Could not create or resolve framework: " + framework.name());
            }
            if (!loadFrameworkIds(projectId).contains(frameworkId)) {
                insertProjectFramework(projectId, frameworkId);
            }
        }
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

    private List<String> loadFrameworkValues(Long projectId) {
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
            return List.of();
        }
    }

    private Long resolveFrameworkId(Framework framework) {
        String frameworkName = framework.name();
        String code = frameworkName.toLowerCase(Locale.ROOT);
        Long legacyId = switch (framework) {
            case NDI -> 1L;
            case CMMI -> 2L;
        };
        if (frameworkIdExists(legacyId)) {
            return legacyId;
        }
        Long id = resolveFrameworkId(code);
        if (id != null) {
            return id;
        }
        return createFramework(frameworkName, code);
    }

    private boolean frameworkIdExists(Long frameworkId) {
        try {
            Integer count = jdbcTemplate.queryForObject(
                    "select count(*) from framework where id = ?",
                    Integer.class,
                    frameworkId
            );
            return count != null && count > 0;
        } catch (Exception ignored) {
            return false;
        }
    }

    private Long resolveFrameworkId(String code) {
        try {
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
        } catch (Exception ignored) {
            return resolveFrameworkIdByName(code);
        }
    }

    private Long resolveFrameworkIdByName(String code) {
        try {
            List<Long> ids = jdbcTemplate.queryForList(
                    """
                            select id
                            from framework
                            where lower(coalesce(name, '')) = ?
                               or lower(coalesce(name, '')) like ?
                            order by id
                            limit 1
                            """,
                    Long.class,
                    code,
                    "%" + code + "%"
            );
            return ids.isEmpty() ? null : ids.get(0);
        } catch (Exception ignored) {
            return null;
        }
    }

    private Long createFramework(String frameworkName, String code) {
        if (!tryInsertFramework(frameworkName, code)) {
            return null;
        }
        return resolveFrameworkId(code);
    }

    private boolean tryInsertFramework(String frameworkName, String code) {
        try {
            jdbcTemplate.update(
                    "insert into framework(code, name, version, created_at) values (?, ?, ?, now())",
                    code,
                    frameworkName,
                    "1"
            );
            return true;
        } catch (Exception ignored) {
            try {
                jdbcTemplate.update(
                        "insert into framework(name, version, created_at) values (?, ?, now())",
                        frameworkName,
                        "1"
                );
                return true;
            } catch (Exception ignoredAgain) {
                return false;
            }
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

    private static String normalizeEmail(String email) {
        return email == null ? "" : email.trim().toLowerCase(Locale.ROOT);
    }
}