package org.example.pfebackend.assessment.api;

import jakarta.validation.Valid;
import org.example.pfebackend.assessment.MaturityFrameworkDefinitionService;
import org.example.pfebackend.assessment.dto.CreateMaturityFrameworkRequest;
import org.example.pfebackend.staff.StaffService;
import org.example.pfebackend.user.AppUser;
import org.springframework.http.HttpStatus;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.security.oauth2.jwt.Jwt;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.ResponseStatus;
import org.springframework.web.bind.annotation.RestController;

import java.util.List;
import java.util.Map;

@RestController
@RequestMapping("/api/admin/maturity-frameworks")
public class AdminMaturityFrameworkController {

    private final StaffService staffService;
    private final MaturityFrameworkDefinitionService maturityFrameworkDefinitionService;

    public AdminMaturityFrameworkController(
            StaffService staffService,
            MaturityFrameworkDefinitionService maturityFrameworkDefinitionService
    ) {
        this.staffService = staffService;
        this.maturityFrameworkDefinitionService = maturityFrameworkDefinitionService;
    }

    @GetMapping
    public List<Map<String, Object>> list(@AuthenticationPrincipal Jwt jwt) {
        AppUser actor = staffService.requireStaffByEmail(jwt.getSubject());
        return maturityFrameworkDefinitionService.listDefinitions(actor);
    }

    @PostMapping
    @ResponseStatus(HttpStatus.CREATED)
    public Map<String, Object> create(
            @AuthenticationPrincipal Jwt jwt,
            @RequestBody @Valid CreateMaturityFrameworkRequest request
    ) {
        AppUser actor = staffService.requireStaffByEmail(jwt.getSubject());
        return maturityFrameworkDefinitionService.createDefinition(actor, request);
    }
}
