import * as core from '@actions/core';
import * as fs from 'fs';
import { execSync } from 'child_process';

export interface PushShas {
  before?: string;
  after?: string;
}

export class GitDiff {
  constructor(private readonly shas: PushShas) {}

  getChangedFiles(): string[] {
    const { before, after } = this.shas;

    if (before && !/^0+$/.test(before)) {
      try {
        const out = execSync(`git diff --name-only ${before} ${after}`, {
          encoding: 'utf-8',
        });
        return out.trim().split('\n').filter(Boolean);
      } catch {
        core.warning(`git diff ${before}..${after} failed. Falling back to HEAD~1.`);
      }
    }

    try {
      const out = execSync('git diff --name-only HEAD~1 HEAD', {
        encoding: 'utf-8',
      });
      return out.trim().split('\n').filter(Boolean);
    } catch {
      core.warning(
        'Could not compute a git diff (insufficient history). All configured webhooks will fire.'
      );
      return [];
    }
  }
}

export function readEventPayload(): PushShas {
  const eventPath = process.env.GITHUB_EVENT_PATH;
  if (eventPath && fs.existsSync(eventPath)) {
    const payload = JSON.parse(fs.readFileSync(eventPath, 'utf-8'));
    return { before: payload.before, after: payload.after };
  }
  return {};
}
