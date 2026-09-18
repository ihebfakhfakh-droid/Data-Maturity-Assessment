package org.example.pfebackend.user;

import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Propagation;
import org.springframework.transaction.annotation.Transactional;

import java.util.Locale;
import java.util.Optional;

/**
 * Loads {@link AppUser} by email in a <strong>new</strong> read-only transaction so the read always
 * sees data committed by other requests (avoids stale persistence-context / snapshot edge cases
 * right after creating a user).
 */
@Service
public class CommittedAppUserLoader {

    private final AppUserRepository appUserRepository;

    public CommittedAppUserLoader(AppUserRepository appUserRepository) {
        this.appUserRepository = appUserRepository;
    }

    @Transactional(propagation = Propagation.REQUIRES_NEW, readOnly = true)
    public Optional<AppUser> findByEmailInNewTransaction(String rawEmail) {
        if (rawEmail == null || rawEmail.isBlank()) {
            return Optional.empty();
        }
        String email = rawEmail.trim().toLowerCase(Locale.ROOT);
        return appUserRepository.findByEmailIgnoreCase(email);
    }
}
