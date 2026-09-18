package org.example.pfebackend.project;

import java.util.Collections;
import java.util.Set;

/**
 * Frameworks assigned to the client's latest project: built-in enums plus optional custom definitions.
 */
public record ClientProjectEntitlements(Set<Framework> builtinFrameworks, Set<Long> customMaturityFrameworkIds) {

    public ClientProjectEntitlements {
        builtinFrameworks = builtinFrameworks == null ? Set.of() : Collections.unmodifiableSet(builtinFrameworks);
        customMaturityFrameworkIds = customMaturityFrameworkIds == null ? Set.of() : Collections.unmodifiableSet(customMaturityFrameworkIds);
    }

    public boolean isEmpty() {
        return builtinFrameworks.isEmpty() && customMaturityFrameworkIds.isEmpty();
    }
}
