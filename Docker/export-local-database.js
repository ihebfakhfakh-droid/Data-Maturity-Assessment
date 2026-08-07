const { execSync } = require("child_process");
const fs = require("fs");
const path = require("path");

const output = path.join(__dirname, "db", "local-snapshot.sql");
const dbUrl =
  process.env.LOCAL_DATABASE_URL ??
  "postgresql://pfe_user:123456@host.docker.internal:5432/pfe_backend_db";

fs.mkdirSync(path.dirname(output), { recursive: true });

console.log(`Exporting local database from ${dbUrl}`);
console.log(`Output: ${output}`);

const command = [
  "docker run --rm",
  "postgres:17-alpine",
  "pg_dump",
  "--no-owner",
  "--no-acl",
  `"${dbUrl}"`,
].join(" ");

const sql = execSync(command, {
  encoding: "utf8",
  maxBuffer: 100 * 1024 * 1024,
  stdio: ["ignore", "pipe", "inherit"],
});

fs.writeFileSync(output, sql, "utf8");

const lines = sql.trim().split(/\r?\n/).length;
console.log(`Export complete (${lines} lines, ${(sql.length / 1024 / 1024).toFixed(2)} MB).`);
console.log("");
console.log("Import into Docker (fresh volume):");
console.log("  cd Docker");
console.log("  docker compose down -v");
console.log("  docker compose up --build -d");
