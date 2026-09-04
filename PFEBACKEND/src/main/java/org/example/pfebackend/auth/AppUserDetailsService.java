package org.example.pfebackend.auth;

import org.example.pfebackend.user.AppUser;
import org.example.pfebackend.user.CommittedAppUserLoader;
import org.springframework.security.core.userdetails.User;
import org.springframework.security.core.userdetails.UserDetails;
import org.springframework.security.core.userdetails.UserDetailsService;
import org.springframework.security.core.userdetails.UsernameNotFoundException;
import org.springframework.stereotype.Service;

@Service
public class AppUserDetailsService implements UserDetailsService {

    private final CommittedAppUserLoader committedAppUserLoader;

    public AppUserDetailsService(CommittedAppUserLoader committedAppUserLoader) {
        this.committedAppUserLoader = committedAppUserLoader;
    }

    @Override
    public UserDetails loadUserByUsername(String username) throws UsernameNotFoundException {
        AppUser user = committedAppUserLoader.findByEmailInNewTransaction(username)
                .orElseThrow(() -> new UsernameNotFoundException("User not found"));

        return User.builder()
                .username(user.getEmail())
                .password(user.getPassword())
                .roles(user.getRole().name())
                .build();
    }
}
