package org.example.pfebackend.staff;

import jakarta.validation.Valid;
import org.example.pfebackend.staff.dto.AssignConsultantRequest;
import org.example.pfebackend.staff.dto.AddClientRequest;
import org.example.pfebackend.staff.dto.AddProjectFrameworksRequest;
import org.example.pfebackend.staff.dto.CreateConsultantRequest;
import org.example.pfebackend.staff.dto.CreateManagerRequest;
import org.example.pfebackend.staff.dto.CreateProjectRequest;
import org.example.pfebackend.staff.dto.UpdateManagerParentRequest;
import org.example.pfebackend.user.AppUser;
import org.springframework.http.HttpStatus;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.security.oauth2.jwt.Jwt;
import org.springframework.web.bind.annotation.DeleteMapping;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PatchMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.ResponseStatus;
import org.springframework.web.bind.annotation.RestController;

import org.example.pfebackend.user.Role;

import java.util.List;
import java.util.Map;
import java.util.Objects;

@RestController
@RequestMapping("/api/admin/staff")
public class AdminStaffController {

    private final StaffService staffService;

    public AdminStaffController(StaffService staffService) {
        this.staffService = staffService;
    }

    @PostMapping("/managers")
    @ResponseStatus(HttpStatus.CREATED)
    public Map<String, Object> createManager(
            @AuthenticationPrincipal Jwt jwt,
            @RequestBody @Valid CreateManagerRequest request
    ) {
        AppUser actor = staffService.requireStaffByEmail(jwt.getSubject());
        AppUser m = staffService.createManager(actor, request);
        return Map.of(
                "id", m.getId(),
                "email", m.getEmail(),
                "fullName", m.getFullName()
        );
    }

    @GetMapping("/managers")
    public List<Map<String, Object>> listManagers(@AuthenticationPrincipal Jwt jwt) {
        AppUser actor = staffService.requireStaffByEmail(jwt.getSubject());
        return staffService.listManagers(actor);
    }

    @PatchMapping("/managers/{managerId}/manager")
    public Map<String, Object> updateManagerParent(
            @AuthenticationPrincipal Jwt jwt,
            @PathVariable Long managerId,
            @RequestBody UpdateManagerParentRequest request
    ) {
        AppUser actor = staffService.requireStaffByEmail(jwt.getSubject());
        return staffService.updateManagerParent(actor, managerId, request);
    }

    @PostMapping("/consultants")
    @ResponseStatus(HttpStatus.CREATED)
    public Map<String, Object> createConsultant(
            @AuthenticationPrincipal Jwt jwt,
            @RequestBody @Valid CreateConsultantRequest request
    ) {
        AppUser actor = staffService.requireStaffByEmail(jwt.getSubject());
        AppUser c = staffService.createConsultant(actor, request);
        Long managerId = actor.getRole() == Role.MANAGER
                ? actor.getId()
                : Objects.requireNonNull(request.managerId(), "managerId");
        return Map.of(
                "id", c.getId(),
                "email", c.getEmail(),
                "fullName", c.getFullName(),
                "managerId", managerId
        );
    }

    @GetMapping("/consultants")
    public List<Map<String, Object>> listConsultants(
            @AuthenticationPrincipal Jwt jwt,
            @RequestParam(required = false) Long managerId
    ) {
        AppUser actor = staffService.requireStaffByEmail(jwt.getSubject());
        return staffService.listConsultants(actor, managerId);
    }

    @DeleteMapping("/consultants/{consultantId}")
    @ResponseStatus(HttpStatus.NO_CONTENT)
    public void deleteConsultant(
            @AuthenticationPrincipal Jwt jwt,
            @PathVariable Long consultantId
    ) {
        AppUser actor = staffService.requireStaffByEmail(jwt.getSubject());
        staffService.deleteConsultant(actor, consultantId);
    }

    @PatchMapping("/clients/{clientId}/consultant")
    @ResponseStatus(HttpStatus.NO_CONTENT)
    public void assignConsultant(
            @AuthenticationPrincipal Jwt jwt,
            @PathVariable Long clientId,
            @RequestBody @Valid AssignConsultantRequest request
    ) {
        AppUser actor = staffService.requireStaffByEmail(jwt.getSubject());
        staffService.assignConsultantToClient(actor, clientId, request);
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

    @PostMapping("/clients/{clientId}/reset-password")
    public Map<String, Object> resetClientPassword(
            @AuthenticationPrincipal Jwt jwt,
            @PathVariable Long clientId
    ) {
        AppUser actor = staffService.requireStaffByEmail(jwt.getSubject());
        return staffService.resetClientPassword(actor, clientId);
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

    @PostMapping("/clients/{clientId}/frameworks")
    public Map<String, Object> addFrameworksToLatestClientProjectPost(
            @AuthenticationPrincipal Jwt jwt,
            @PathVariable Long clientId,
            @RequestBody AddProjectFrameworksRequest request
    ) {
        AppUser actor = staffService.requireStaffByEmail(jwt.getSubject());
        return staffService.addFrameworksToLatestClientProject(actor, clientId, request);
    }
}
