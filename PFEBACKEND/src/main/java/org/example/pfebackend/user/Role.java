package org.example.pfebackend.user;

public enum Role {
    CLIENT,
    /** Highest staff priority: can create managers, full access. */
    ADMIN,
    /** Can create/delete consultants in their team, see all clients with submissions, assign clients to consultants. */
    MANAGER,
    /** Sees only clients assigned to them (with submitted assessments). */
    CONSULTANT
}
