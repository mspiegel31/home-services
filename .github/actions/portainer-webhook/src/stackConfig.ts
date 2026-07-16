import * as core from '@actions/core';
import * as yaml from 'js-yaml';
import * as fs from 'fs';

export interface TriggerTarget {
  subdir: string;
  webhookId: string;
}

interface WebhookEntry {
  path: string;
  uuid: string;
}

interface WebhookConfigFile {
  webhooks: WebhookEntry[];
}

export class StackConfig {
  private readonly webhooks: WebhookEntry[];

  constructor(configPath: string) {
    let config: WebhookConfigFile;
    try {
      config = yaml.load(fs.readFileSync(configPath, 'utf-8')) as WebhookConfigFile;
    } catch (err) {
      throw new Error(`Failed to read config file ${configPath}: ${(err as Error).message}`);
    }

    const webhooks = config?.webhooks;
    if (!webhooks || !Array.isArray(webhooks)) {
      throw new Error("Config file must contain a 'webhooks' list of { path, uuid } entries");
    }

    this.webhooks = webhooks;
  }

  resolveTargets(changedFiles: string[]): TriggerTarget[] {
    if (this.webhooks.length === 0) {
      core.info('No webhooks configured. Nothing to do.');
      return [];
    }

    const targets: TriggerTarget[] = [];

    for (const { path: subdir, uuid } of this.webhooks) {
      if (!subdir || !uuid) {
        core.warning(`Skipping entry with missing path or uuid: ${JSON.stringify({ subdir, uuid })}`);
        continue;
      }

      const hasChange =
        changedFiles.length === 0 || changedFiles.some((f) => this.isPathUnderDir(f, subdir));

      if (hasChange) {
        targets.push({ subdir, webhookId: uuid });
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
