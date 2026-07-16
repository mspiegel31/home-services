import * as https from 'https';
import * as http from 'http';
import { WebhookHttpError, WebhookConnectionError } from './errors';

export interface WebhookResult {
  status: number;
  body: string;
}

export class WebhookClient {
  private readonly baseUrl: string;
  private readonly headers: Record<string, string>;

  constructor(baseUrl: string, headers: Record<string, string> = {}) {
    this.baseUrl = baseUrl.replace(/\/$/, '');
    this.headers = headers;
  }

  async trigger(webhookId: string): Promise<WebhookResult> {
    const fullUrl = `${this.baseUrl}/api/stacks/webhooks/${webhookId}`;
    const parsed = new URL(fullUrl);
    const isHttps = parsed.protocol === 'https:';
    const mod = isHttps ? https : http;

    return new Promise<WebhookResult>((resolve, reject) => {
      const options = {
        method: 'POST' as const,
        hostname: parsed.hostname,
        port: parsed.port || (isHttps ? 443 : 80),
        path: parsed.pathname,
        headers: { ...this.headers, 'Content-Length': 0 },
      };

      const req = mod.request(options, (res) => {
        let body = '';
        res.on('data', (chunk: Buffer) => (body += chunk));
        res.on('end', () => {
          if (res.statusCode && res.statusCode >= 200 && res.statusCode < 300) {
            resolve({ status: res.statusCode, body });
          } else {
            reject(
              new WebhookHttpError(
                `HTTP ${res.statusCode}: ${body || '(no body)'}`,
                res.statusCode ?? 0,
                body
              )
            );
          }
        });
      });

      req.on('error', (err: NodeJS.ErrnoException) =>
        reject(new WebhookConnectionError(err.code || err.message, err.code || 'UNKNOWN'))
      );

      req.end();
    });
  }
}
