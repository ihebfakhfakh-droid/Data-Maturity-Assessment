package org.example.pfebackend.auth.dto;

import org.example.pfebackend.user.Role;

import java.time.Instant;

public record AuthResponse(
        String accessToken,
        String tokenType,
        Instant expiresAt,
        String email,
        String fullName,
        Role role
) {
}
