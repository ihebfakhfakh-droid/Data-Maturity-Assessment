package org.example.pfebackend.project.api;

import jakarta.validation.Valid;
import org.example.pfebackend.assessment.AssessmentService;
import org.example.pfebackend.staff.StaffService;
import org.example.pfebackend.staff.dto.AddClientRequest;
import org.example.pfebackend.staff.dto.AddProjectConsultantRequest;
import org.example.pfebackend.staff.dto.AddProjectFrameworksRequest;
import org.example.pfebackend.staff.dto.CreateProjectRequest;
import org.example.pfebackend.user.AppUser;
import org.example.pfebackend.user.AppUserRepository;
import org.springframework.http.HttpStatus;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.security.oauth2.jwt.Jwt;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PatchMapping;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.PutMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.ResponseStatus;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.server.ResponseStatusException;

import java.util.List;
import java.util.Map;

/**
 * Compatibility endpoints for the Staff/Admin UI.
 * Some frontends call /api/admin/projects instead of /api/admin/staff/projects.
 */
@RestController
@RequestMapping("/api/admin")
public class AdminProjectController {

    private final StaffService staffService;
    private final AppUserRepository userRepository;
    private final AssessmentService assessmentService;

    public AdminProjectController(
            StaffService staffService,
            AppUserRepository userRepository,
            AssessmentService assessmentService
    ) {
        this.staffService = staffService;
        this.userRepository = userRepository;
        this.assessmentService = assessmentService;
    }

    @PostMapping("/projects")
    @ResponseStatus(HttpStatus.CREATED)
    public Map<String, Object> createProject(
            @AuthenticationPrincipal Jwt jwt,
            @RequestBody @Valid CreateProjectRequest request
    ) {
        AppUser actor = staffService.requireStaffByEmail(jwt.getSubject());
        return staffService.createNewProject(actor, request);
    }

    @GetMapping("/projects/{projectId}")
    public Map<String, Object> getProject(
            @AuthenticationPrincipal Jwt jwt,
            @PathVariable Long projectId
    ) {
        AppUser actor = staffService.requireStaffByEmail(jwt.getSubject());
        return staffService.getProjectSummary(actor, projectId);
    }

    @GetMapping("/clients/{clientId}/project")
    public Map<String, Object> getLatestClientProject(
            @AuthenticationPrincipal Jwt jwt,
            @PathVariable Long clientId
    ) {
        AppUser actor = staffService.requireStaffByEmail(jwt.getSubject());
        return staffService.getLatestClientProjectSummary(actor, clientId);
    }

    @PatchMapping("/projects/{projectId}/frameworks")
    public Map<String, Object> addFrameworksToProject(
            @AuthenticationPrincipal Jwt jwt,
            @PathVariable Long projectId,
            @RequestBody AddProjectFrameworksRequest request
    ) {
        AppUser actor = staffService.requireStaffByEmail(jwt.getSubject());
        return staffService.addFrameworksToProject(actor, projectId, request);
    }

    @PatchMapping("/clients/{clientId}/project/frameworks")
    public Map<String, Object> addFrameworksToLatestClientProject(
            @AuthenticationPrincipal Jwt jwt,
            @PathVariable Long clientId,
            @RequestBody AddProjectFrameworksRequest request
    ) {
        AppUser actor = staffService.requireStaffByEmail(jwt.getSubject());
        return staffService.addFrameworksToLatestClientProject(actor, clientId, request);
    }

    @GetMapping("/clients/{clientId}/frameworks")
    public List<Map<String, Object>> listFrameworksForLatestClientProject(
            @AuthenticationPrincipal Jwt jwt,
            @PathVariable Long clientId
    ) {
        AppUser actor = staffService.requireStaffByEmail(jwt.getSubject());
        return staffService.listFrameworksForLatestClientProject(actor, clientId);
    }

    @GetMapping("/projects/{projectId}/consultants")
    public List<Map<String, Object>> listProjectConsultants(
            @AuthenticationPrincipal Jwt jwt,
            @PathVariable Long projectId
    ) {
        AppUser actor = staffService.requireStaffByEmail(jwt.getSubject());
        return staffService.listProjectConsultants(actor, projectId);
    }

    @GetMapping("/projects/{projectId}/consultants/available")
    public List<Map<String, Object>> listAvailableProjectConsultants(
            @AuthenticationPrincipal Jwt jwt,
            @PathVariable Long projectId
    ) {
        AppUser actor = staffService.requireStaffByEmail(jwt.getSubject());
        return staffService.listAvailableProjectConsultants(actor, projectId);
    }

    @PostMapping("/projects/{projectId}/consultants")
    public Map<String, Object> addConsultantToProject(
            @AuthenticationPrincipal Jwt jwt,
            @PathVariable Long projectId,
            @RequestBody @Valid AddProjectConsultantRequest request
    ) {
        AppUser actor = staffService.requireStaffByEmail(jwt.getSubject());
        return staffService.addConsultantToProject(actor, projectId, request);
    }

    @GetMapping("/clients/{clientId}/project/consultants")
    public List<Map<String, Object>> listLatestClientProjectConsultants(
            @AuthenticationPrincipal Jwt jwt,
            @PathVariable Long clientId
    ) {
        AppUser actor = staffService.requireStaffByEmail(jwt.getSubject());
        return staffService.listLatestClientProjectConsultants(actor, clientId);
    }

    @GetMapping("/clients/{clientId}/project/consultants/available")
    public List<Map<String, Object>> listAvailableLatestClientProjectConsultants(
            @AuthenticationPrincipal Jwt jwt,
            @PathVariable Long clientId
    ) {
        AppUser actor = staffService.requireStaffByEmail(jwt.getSubject());
        return staffService.listAvailableLatestClientProjectConsultants(actor, clientId);
    }

    @PostMapping("/clients/{clientId}/project/consultants")
    public Map<String, Object> addConsultantToLatestClientProject(
            @AuthenticationPrincipal Jwt jwt,
            @PathVariable Long clientId,
            @RequestBody @Valid AddProjectConsultantRequest request
    ) {
        AppUser actor = staffService.requireStaffByEmail(jwt.getSubject());
        return staffService.addConsultantToLatestClientProject(actor, clientId, request);
    }

    @PostMapping("/clients/{clientId}/frameworks")
    public Map<String, Object> addFrameworksToLatestClientProjectPost(
            @AuthenticationPrincipal Jwt jwt,
            @PathVariable Long clientId,
            @RequestBody AddProjectFrameworksRequest request
    ) {
        AppUser actor = staffService.requireStaffByEmail(jwt.getSubject());
        return staffService.addFrameworksToLatestClientProject(actor, clientId, request);
    }

    @PostMapping("/clients")
    @ResponseStatus(HttpStatus.CREATED)
    public Map<String, Object> addClient(
            @AuthenticationPrincipal Jwt jwt,
            @RequestBody @Valid AddClientRequest request
    ) {
        AppUser actor = staffService.requireStaffByEmail(jwt.getSubject());
        return staffService.addNewClient(actor, request);
    }

    @PutMapping("/clients")
    public Map<String, Object> putClientPlural(
            @AuthenticationPrincipal Jwt jwt,
            @RequestBody @Valid AddClientRequest request
    ) {
        AppUser actor = staffService.requireStaffByEmail(jwt.getSubject());
        return staffService.addNewClient(actor, request);
    }

    @GetMapping("/clients")
    public List<Map<String, Object>> listClients(@AuthenticationPrincipal Jwt jwt) {
        AppUser actor = staffService.requireStaffByEmail(jwt.getSubject());
        return staffService.listAllClients(actor);
    }

    @GetMapping("/clients/project-scope")
    public List<Map<String, Object>> listProjectScopedClients(@AuthenticationPrincipal Jwt jwt) {
        AppUser actor = staffService.requireStaffByEmail(jwt.getSubject());
        return staffService.listProjectScopedClients(actor);
    }

    @GetMapping("/client")
    public List<Map<String, Object>> listClientsSingular(@AuthenticationPrincipal Jwt jwt) {
        AppUser actor = staffService.requireStaffByEmail(jwt.getSubject());
        return staffService.listAllClients(actor);
    }

    // Compatibility: older UI calls /api/admin/clients/{id}/assessments
    @GetMapping("/clients/{clientId}/assessments")
    public List<Map<String, Object>> assessmentsByClientCompat(
            @AuthenticationPrincipal Jwt jwt,
            @PathVariable Long clientId
    ) {
        AppUser staff = staffService.requireStaffByEmail(jwt.getSubject());
        AppUser client = userRepository.findById(clientId)
                .orElseThrow(() -> new ResponseStatusException(HttpStatus.NOT_FOUND, "Client not found"));
        staffService.assertCanAccessClientData(staff, client);

        return assessmentService.listMainAssessmentSummariesForClient(client);
    }

    // Compatibility: some frontends call singular /client and use PUT.
    @PostMapping("/client")
    @ResponseStatus(HttpStatus.CREATED)
    public Map<String, Object> addClientSingular(
            @AuthenticationPrincipal Jwt jwt,
            @RequestBody @Valid AddClientRequest request
    ) {
        AppUser actor = staffService.requireStaffByEmail(jwt.getSubject());
        return staffService.addNewClient(actor, request);
    }

    @PutMapping("/client")
    public Map<String, Object> putClientSingular(
            @AuthenticationPrincipal Jwt jwt,
            @RequestBody @Valid AddClientRequest request
    ) {
        AppUser actor = staffService.requireStaffByEmail(jwt.getSubject());
        return staffService.addNewClient(actor, request);
    }
}

