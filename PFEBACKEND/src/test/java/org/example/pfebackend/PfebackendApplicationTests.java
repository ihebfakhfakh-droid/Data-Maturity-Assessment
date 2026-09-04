package org.example.pfebackend;

import org.example.pfebackend.staff.StaffService;
import org.example.pfebackend.user.AppUser;
import org.example.pfebackend.user.Role;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.web.servlet.mvc.method.RequestMappingInfo;
import org.springframework.web.servlet.mvc.method.annotation.RequestMappingHandlerMapping;

import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.Set;
import java.util.stream.Collectors;
import java.util.stream.Stream;

import static org.assertj.core.api.Assertions.assertThat;
import static org.junit.jupiter.api.Assumptions.assumeTrue;

@SpringBootTest
class PfebackendApplicationTests {

	@Autowired
	private RequestMappingHandlerMapping requestMappingHandlerMapping;

	@Autowired
	private StaffService staffService;

	@Autowired
	private JdbcTemplate jdbcTemplate;

	@Test
	void contextLoads() {
	}

	@Test
	void adminClientFrameworkEndpointsAreRegistered() {
		Set<String> paths = requestMappingHandlerMapping.getHandlerMethods().keySet().stream()
				.flatMap(this::pathsFor)
				.collect(Collectors.toSet());

		assertThat(paths).contains("/api/admin/clients/{clientId}/frameworks");
	}

	@Test
	void acceptanceCriteriaReportEndpointIsRegistered() {
		Set<String> paths = requestMappingHandlerMapping.getHandlerMethods().keySet().stream()
				.flatMap(this::pathsFor)
				.collect(Collectors.toSet());

		assertThat(paths).contains("/api/staff/evidences/{evidenceId}/acceptance-criteria-report");
	}

	@Test
	void client24LatestProject16ReturnsNdiAndCmmiWhenFixtureExists() {
		assumeTrue(countRows("select count(*) from app_user where id = 24") == 1);
		assumeTrue(countRows("select count(*) from project where id = 16 and client_id = 24") == 1);
		assumeTrue(countRows("select count(*) from project_framework where project_id = 16 and framework_id in (1, 2)") == 2);
		assumeTrue(Long.valueOf(16L).equals(latestProjectIdForClient24()));

		AppUser admin = new AppUser();
		admin.setRole(Role.ADMIN);
		List<Map<String, Object>> frameworks = staffService.listFrameworksForLatestClientProject(admin, 24L);

		Set<String> codes = frameworks.stream()
				.map(row -> String.valueOf(row.get("code")).toUpperCase(Locale.ROOT))
				.collect(Collectors.toSet());
		assertThat(codes).contains("NDI", "CMMI");
	}

	private Stream<String> pathsFor(RequestMappingInfo mappingInfo) {
		return mappingInfo.getPathPatternsCondition().getPatterns().stream()
				.map(pattern -> pattern.getPatternString());
	}

	private int countRows(String sql) {
		try {
			Integer count = jdbcTemplate.queryForObject(sql, Integer.class);
			return count == null ? 0 : count;
		} catch (Exception ignored) {
			return 0;
		}
	}

	private Long latestProjectIdForClient24() {
		try {
			return jdbcTemplate.queryForObject(
					"select id from project where client_id = 24 order by created_at desc nulls last, id desc limit 1",
					Long.class
			);
		} catch (Exception ignored) {
			try {
				return jdbcTemplate.queryForObject(
						"select id from project where client_id = 24 order by id desc limit 1",
						Long.class
				);
			} catch (Exception ignoredAgain) {
				return null;
			}
		}
	}

}
