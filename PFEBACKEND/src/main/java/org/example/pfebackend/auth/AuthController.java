package org.example.pfebackend.auth;

import jakarta.validation.Valid;
import org.example.pfebackend.auth.dto.AuthResponse;
import org.example.pfebackend.auth.dto.LoginRequest;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.server.ResponseStatusException;

import java.util.Map;

@RestController
@RequestMapping("/api/auth")
public class AuthController {

    private final AuthService authService;

    public AuthController(AuthService authService) {
        this.authService = authService;
    }

    @PostMapping("/login")
    public ResponseEntity<?> login(@RequestBody @Valid LoginRequest request) {
        try {
            AuthResponse response = authService.login(request);
            return ResponseEntity.ok(response);
        } catch (ResponseStatusException ex) {
            String message = ex.getReason() == null ? "Login failed" : ex.getReason();
            return ResponseEntity.status(ex.getStatusCode())
                    .body(Map.of("message", message));
        }
    }
}
