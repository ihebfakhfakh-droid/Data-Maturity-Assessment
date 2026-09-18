package org.example.pfebackend.evidence;

import org.springframework.data.jpa.repository.JpaRepository;

import java.util.List;

public interface EvidenceRepository extends JpaRepository<Evidence, Long> {
    List<Evidence> findByAnswer_IdOrderByCreatedAtAscIdAsc(Long answerId);
}

