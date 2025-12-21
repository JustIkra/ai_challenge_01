import { execSync } from "child_process";

const PROJECT_DIR = process.env.PROJECT_DIR || process.cwd();

/**
 * Execute a command and return result object
 * @param {string} command - Command to execute
 * @returns {{ success: boolean, output?: string, error?: string }}
 */
function execute(command) {
  try {
    const output = execSync(command, {
      encoding: "utf-8",
      cwd: PROJECT_DIR
    });
    return { success: true, output: output.trim() };
  } catch (err) {
    const errorMessage = err.stderr || err.stdout || err.message || String(err);
    return { success: false, error: errorMessage.trim() };
  }
}

/**
 * Start containers with docker compose up -d
 * @param {string} [service] - Optional service name to start
 * @returns {{ success: boolean, output?: string, error?: string }}
 */
export function composeUp(service) {
  const cmd = service
    ? `docker compose up -d ${service}`
    : `docker compose up -d`;
  return execute(cmd);
}

/**
 * Stop containers with docker compose down
 * @param {boolean} [volumes=false] - Whether to remove volumes
 * @returns {{ success: boolean, output?: string, error?: string }}
 */
export function composeDown(volumes = false) {
  const cmd = volumes
    ? `docker compose down -v`
    : `docker compose down`;
  return execute(cmd);
}

/**
 * List containers with docker compose ps -a
 * @returns {{ success: boolean, output?: string, error?: string }}
 */
export function composePs() {
  return execute(`docker compose ps -a`);
}

/**
 * Build and start containers with docker compose up -d --build
 * @param {string} [service] - Optional service name to build
 * @returns {{ success: boolean, output?: string, error?: string }}
 */
export function composeBuild(service) {
  const cmd = service
    ? `docker compose up -d --build ${service}`
    : `docker compose up -d --build`;
  return execute(cmd);
}

/**
 * Get logs from a service
 * @param {string} service - Service name
 * @param {number} [lines=100] - Number of lines to tail
 * @returns {{ success: boolean, output?: string, error?: string }}
 */
export function composeLogs(service, lines = 100) {
  return execute(`docker compose logs --tail=${lines} ${service}`);
}

/**
 * Restart a service
 * @param {string} service - Service name to restart
 * @returns {{ success: boolean, output?: string, error?: string }}
 */
export function composeRestart(service) {
  return execute(`docker compose restart ${service}`);
}

/**
 * Execute a command in a running container
 * @param {string} service - Service name
 * @param {string} command - Command to execute
 * @param {string} [workdir] - Optional working directory inside container
 * @returns {{ success: boolean, output?: string, error?: string }}
 */
export function composeExec(service, command, workdir) {
  const workdirFlag = workdir ? `-w ${workdir}` : "";
  const cmd = `docker compose exec -T ${workdirFlag} ${service} ${command}`.trim();
  return execute(cmd);
}
