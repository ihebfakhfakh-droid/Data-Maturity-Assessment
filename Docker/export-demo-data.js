const { execSync } = require("child_process");
const fs = require("fs");
const path = require("path");

const sqlFile = path.join(__dirname, "export-demo-assessment-answers.sql");
const output = path.join(__dirname, "..", "PFEBACKEND", "src", "main", "resources", "db", "demo-assessment-answers.csv");

const command = [
  "docker run --rm",
  `-v "${sqlFile.replace(/\\/g, "/")}:/export.sql:ro"`,
  "postgres:16-alpine",
  `sh -c "psql 'postgresql://pfe_user:123456@host.docker.internal:5432/pfe_backend_db' -f /export.sql"`,
].join(" ");

const csv = execSync(command, { encoding: "utf8" });
fs.writeFileSync(output, csv, "utf8");
console.log(`Wrote ${csv.trim().split(/\r?\n/).length} rows to ${output}`);
