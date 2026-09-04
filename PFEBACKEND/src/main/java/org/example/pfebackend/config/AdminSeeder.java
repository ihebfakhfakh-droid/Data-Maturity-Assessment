package org.example.pfebackend.config;

import org.example.pfebackend.user.AppUser;
import org.example.pfebackend.user.AppUserRepository;
import org.example.pfebackend.user.Role;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.boot.CommandLineRunner;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.stereotype.Component;

import java.util.Locale;

@Component
public class AdminSeeder implements CommandLineRunner {

    private final AppUserRepository appUserRepository;
    private final PasswordEncoder passwordEncoder;

    @Value("${app.auth.bootstrap.enabled:false}")
    private boolean bootstrapEnabled;

    @Value("${app.auth.bootstrap.admin-email:admin@pfe.local}")
    private String adminEmail;

    @Value("${app.auth.bootstrap.admin-password:Admin@12345}")
    private String adminPassword;

    @Value("${app.auth.bootstrap.admin-full-name:Super Admin}")
    private String adminFullName;

    public AdminSeeder(AppUserRepository appUserRepository, PasswordEncoder passwordEncoder) {
        this.appUserRepository = appUserRepository;
        this.passwordEncoder = passwordEncoder;
    }

    @Override
    public void run(String... args) {
        if (!bootstrapEnabled) {
            return;
        }
        if (adminEmail == null || adminEmail.isBlank() || adminPassword == null || adminPassword.isBlank()) {
            return;
        }

        if (appUserRepository.existsByEmailIgnoreCase(adminEmail)) {
            return;
        }

        AppUser admin = new AppUser();
        admin.setFullName(adminFullName);
        admin.setEmail(adminEmail.trim().toLowerCase(Locale.ROOT));
        admin.setPassword(passwordEncoder.encode(adminPassword));
        admin.setRole(Role.ADMIN);
        appUserRepository.save(admin);
    }
}
