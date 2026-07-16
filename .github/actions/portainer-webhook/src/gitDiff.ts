import * as core from '@actions/core';
import * as exec from '@actions/exec';
import * as fs from 'fs';

export interface PushShas {
  before?: string;
  after?: string;
}

export class GitDiff {
  constructor(private readonly shas: PushShas) {}

  async getChangedFiles(): Promise<string[]> {
    const { before, after } = this.shas;

    if (before && !/^0+$/.test(before)) {
      const head = after || process.env.GITHUB_SHA;
      if (head) {
        try {
          const { stdout } = await exec.getExecOutput(
            'git',
            ['diff', '--no-renames', '--name-only', '-z', before, head],
            { silent: !core.isDebug() }
          );
          return this.parseNullTerminated(stdout);
        } catch {
          core.warning(`git diff ${before}..${head} failed. Falling back to HEAD~1.`);
        }
      }
    }

    try {
      const { stdout } = await exec.getExecOutput(
        'git',
        ['diff', '--no-renames', '--name-only', '-z', 'HEAD~1', 'HEAD'],
        { silent: !core.isDebug() }
      );
      return this.parseNullTerminated(stdout);
    } catch {
      core.warning(
        'Could not compute a git diff (insufficient history). All configured webhooks will fire.'
      );
      return [];
    }
  }

  private parseNullTerminated(stdout: string): string[] {
    return stdout.split('\0').filter(Boolean);
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
