package org.example.pfebackend.staff.dto;

import com.fasterxml.jackson.annotation.JsonAlias;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Size;
import org.example.pfebackend.project.Framework;

import java.util.Set;

public record CreateProjectRequest(
        @NotNull Long clientId,
        @JsonAlias({"projectName", "title"}) @Size(max = 200) String name,
        /** Built-in frameworks (NDI, CMMI). May be empty if {@link #customMaturityFrameworkIds} is non-empty. */
        Set<Framework> frameworks,
        /** IDs of {@link org.example.pfebackend.assessment.MaturityFrameworkDefinition} created by an admin. */
        Set<Long> customMaturityFrameworkIds,
        /** Optional user assigned to the project as consultant. Can be a CONSULTANT or MANAGER. */
        Long consultantId,
        /** Whether the assigned user can manage this project in addition to working on it. */
        Boolean canManageProject
) {}

