package org.example.pfebackend.staff.dto;

import jakarta.validation.constraints.NotNull;

public record AssignConsultantRequest(@NotNull Long consultantId) {
}
