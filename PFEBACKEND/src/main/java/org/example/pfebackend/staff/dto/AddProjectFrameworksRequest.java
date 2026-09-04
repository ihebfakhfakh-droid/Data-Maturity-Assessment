package org.example.pfebackend.staff.dto;

import com.fasterxml.jackson.annotation.JsonAlias;
import org.example.pfebackend.project.Framework;

import java.util.Set;

public record AddProjectFrameworksRequest(
        /** Built-in frameworks to add to the existing project. */
        @JsonAlias({"builtinFrameworks", "frameworksToAdd"})
        Set<Framework> frameworks,
        /** Single built-in framework, for UIs that send one selection at a time. */
        @JsonAlias({"framework", "builtinFramework", "selectedFramework", "frameworkCode", "code", "value"})
        Framework framework,
        /** IDs of admin-defined maturity frameworks to add to the existing project. */
        @JsonAlias({"customFrameworkIds", "maturityFrameworkIds", "customFrameworksToAdd"})
        Set<Long> customMaturityFrameworkIds,
        /** Single custom framework id, for UIs that send one selection at a time. */
        @JsonAlias({"customMaturityFrameworkId", "customFrameworkId", "maturityFrameworkId", "selectedCustomFrameworkId"})
        Long customMaturityFrameworkId
) {}
