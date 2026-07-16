import * as core from '@actions/core';
import * as yaml from 'js-yaml';
import * as fs from 'fs';

export interface TriggerTarget {
  subdir: string;
  webhookId: string;
}

interface StackConfigFile {
  stacks: Record<string, string>;
}

export class StackConfig {
  private readonly stacks: Record<string, string>;

  constructor(configPath: string) {
    let config: StackConfigFile;
    try {
      config = yaml.load(fs.readFileSync(configPath, 'utf-8')) as StackConfigFile;
    } catch (err) {
      throw new Error(`Failed to read config file ${configPath}: ${(err as Error).message}`);
    }

    const stacks = config?.stacks;
    if (!stacks || typeof stacks !== 'object' || Array.isArray(stacks)) {
      throw new Error(
        "Config file must contain a 'stacks' mapping of subdirectory -> env var name"
      );
    }

    this.stacks = stacks;
  }

  resolveTargets(
    changedFiles: string[],
    env: Record<string, string>
  ): TriggerTarget[] {
    const entries = Object.entries(this.stacks);
    if (entries.length === 0) {
      core.info('No stacks configured. Nothing to do.');
      return [];
    }

    const targets: TriggerTarget[] = [];

    for (const [subdir, envVarName] of entries) {
      if (typeof envVarName !== 'string') {
        core.warning(`Stack '${subdir}' maps to a non-string value. Skipping.`);
        continue;
      }

      const webhookId = env[envVarName];
      if (!webhookId) {
        core.warning(`Env var '${envVarName}' for stack '${subdir}' is not set. Skipping.`);
        continue;
      }

      const hasChange =
        changedFiles.length === 0 || changedFiles.some((f) => this.isPathUnderDir(f, subdir));

      if (hasChange) {
        targets.push({ subdir, webhookId });
      }
    }

    return targets;
  }

  private isPathUnderDir(filePath: string, dir: string): boolean {
    const f = filePath.replace(/^\.\//, '');
    const d = dir.replace(/\/$/, '');
    return f === d || f.startsWith(d + '/');
  }
}
