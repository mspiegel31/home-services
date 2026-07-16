import * as core from '@actions/core';
import * as path from 'path';
import { StackConfig } from './src/stackConfig';
import { GitDiff, readEventPayload } from './src/gitDiff';
import { WebhookClient } from './src/webhookClient';
import { WebhookHttpError, WebhookConnectionError } from './src/errors';

async function run(): Promise<void> {
  try {
    const configFile = core.getInput('config-file') || '.github/portainer-webhooks.yml';
    const baseUrl = core.getInput('base-url', { required: true });
    const cfClientId = core.getInput('cf-access-client-id');
    const cfClientSecret = core.getInput('cf-access-client-secret');
    const failFast = core.getInput('fail-fast') === 'true';

    // --- Load config ------------------------------------------------------
    const configPath = path.resolve(process.cwd(), configFile);
    const config = new StackConfig(configPath);

    // --- Detect changed files --------------------------------------------
    const payload = readEventPayload();
    const diff = new GitDiff(payload);
    const changedFiles = await diff.getChangedFiles();

    if (changedFiles.length === 0) {
      core.info('No diff available — will trigger all configured webhooks.');
    } else {
      core.info(
        `Changed files (${changedFiles.length}):\n${changedFiles.map((f) => '  ' + f).join('\n')}`
      );
    }

    // --- Resolve which stacks to trigger ---------------------------------
    const targets = config.resolveTargets(changedFiles);

    if (targets.length === 0) {
      core.info('No stacks matched the changed files. Nothing to trigger.');
      core.setOutput('triggered', '');
      return;
    }

    core.info(
      `Triggering ${targets.length} webhook(s): ${targets.map((t) => t.subdir).join(', ')}`
    );

    // --- Build client + fire webhooks ------------------------------------
    const headers: Record<string, string> = {};
    if (cfClientId && cfClientSecret) {
      headers['CF-Access-Client-Id'] = cfClientId;
      headers['CF-Access-Client-Secret'] = cfClientSecret;
    }

    const client = new WebhookClient(baseUrl, headers);

    const triggered: string[] = [];
    const failed: string[] = [];

    for (const { subdir, webhookId } of targets) {
      try {
        core.info(`POST ${subdir} -> ${baseUrl}/api/stacks/webhooks/${webhookId}`);
        const result = await client.trigger(webhookId);
        core.info(`  ok  ${subdir} - HTTP ${result.status}${result.body ? ` ${result.body}` : ''}`);
        triggered.push(subdir);
      } catch (err) {
        if (err instanceof WebhookHttpError) {
          core.error(`  FAIL ${subdir} - HTTP ${err.statusCode}: ${err.body || '(no body)'}`);
        } else if (err instanceof WebhookConnectionError) {
          core.error(`  FAIL ${subdir} - ${err.code}`);
        } else {
          core.error(`  FAIL ${subdir} - ${(err as Error).message}`);
        }
        failed.push(subdir);
        if (failFast) {
          core.setFailed(`Webhook failed for ${subdir}: ${(err as Error).message}`);
          return;
        }
      }
    }

    core.setOutput('triggered', triggered.join(','));

    if (failed.length > 0) {
      core.setFailed(`${failed.length} webhook(s) failed: ${failed.join(', ')}`);
    } else if (triggered.length > 0) {
      core.info(`All ${triggered.length} webhook(s) succeeded.`);
    }
  } catch (err) {
    core.setFailed((err as Error).message);
  }
}

run();
