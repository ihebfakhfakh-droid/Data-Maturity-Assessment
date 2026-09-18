package org.example.pfebackend.staff.dto;

import jakarta.validation.constraints.NotNull;

public record AddProjectConsultantRequest(
        @NotNull Long consultantId,
        Boolean canManageProject
) {
}
