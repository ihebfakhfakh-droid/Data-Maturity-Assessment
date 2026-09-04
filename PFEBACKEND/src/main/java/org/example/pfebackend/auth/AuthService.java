package org.example.pfebackend.auth;

import org.example.pfebackend.auth.dto.AuthResponse;
import org.example.pfebackend.auth.dto.LoginRequest;
import org.example.pfebackend.user.AppUser;
import org.example.pfebackend.user.CommittedAppUserLoader;
import org.springframework.http.HttpStatus;
import org.springframework.security.authentication.BadCredentialsException;
import org.springframework.security.authentication.AuthenticationManager;
import org.springframework.security.authentication.UsernamePasswordAuthenticationToken;
import org.springframework.stereotype.Service;
import org.springframework.web.server.ResponseStatusException;

import java.util.Locale;
import java.util.regex.Pattern;

@Service
public class AuthService {

    private static final String EMAIL_NOT_REGISTERED_MESSAGE =
            "This email is invalid or is not registered in the database.";
    private static final String INCORRECT_PASSWORD_MESSAGE = "Incorrect password.";
    private static final Pattern EMAIL_PATTERN = Pattern.compile("^[^\\s@]+@[^\\s@]+$");

    private final AuthenticationManager authenticationManager;
    private final CommittedAppUserLoader committedAppUserLoader;
    private final JwtService jwtService;

    public AuthService(
            AuthenticationManager authenticationManager,
            CommittedAppUserLoader committedAppUserLoader,
            JwtService jwtService
    ) {
        this.authenticationManager = authenticationManager;
        this.committedAppUserLoader = committedAppUserLoader;
        this.jwtService = jwtService;
    }

    public AuthResponse login(LoginRequest request) {
        String email = normalizeEmail(request.email());
        if (!isValidEmail(email)) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, EMAIL_NOT_REGISTERED_MESSAGE);
        }

        AppUser user = committedAppUserLoader.findByEmailInNewTransaction(email)
                .orElseThrow(() -> new ResponseStatusException(HttpStatus.BAD_REQUEST, EMAIL_NOT_REGISTERED_MESSAGE));

        try {
            authenticationManager.authenticate(new UsernamePasswordAuthenticationToken(email, request.password()));
        } catch (BadCredentialsException ex) {
            throw new ResponseStatusException(HttpStatus.UNAUTHORIZED, INCORRECT_PASSWORD_MESSAGE);
        }

        return toAuthResponse(user);
    }

    private AuthResponse toAuthResponse(AppUser user) {
        JwtService.IssuedToken issuedToken = jwtService.issueToken(user);
        return new AuthResponse(
                issuedToken.value(),
                "Bearer",
                issuedToken.expiresAt(),
                user.getEmail(),
                user.getFullName(),
                user.getRole()
        );
    }

    private String normalizeEmail(String email) {
        return email == null ? "" : email.trim().toLowerCase(Locale.ROOT);
    }

    private boolean isValidEmail(String email) {
        return EMAIL_PATTERN.matcher(email).matches();
    }
}
