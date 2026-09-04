package org.example.pfebackend.staff.dto;

import jakarta.validation.constraints.Email;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Size;

public record CreateManagerRequest(
        @NotBlank @Size(min = 2, max = 120) String fullName,
        @NotBlank @Email String email,
        @NotBlank @Size(min = 8, max = 128) String password,
        Long managerId
) {
}
