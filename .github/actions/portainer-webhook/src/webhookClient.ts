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

    let response: Response;
    try {
      response = await fetch(fullUrl, {
        method: 'POST',
        headers: this.headers,
      });
    } catch (err) {
      const cause = (err as Error & { cause?: NodeJS.ErrnoException }).cause;
      throw new WebhookConnectionError(
        cause?.code || (err as Error).message,
        cause?.code || 'UNKNOWN'
      );
    }

    const body = await response.text();

    if (response.ok) {
      return { status: response.status, body };
    }

    throw new WebhookHttpError(
      `HTTP ${response.status}: ${body || '(no body)'}`,
      response.status,
      body
    );
  }
}
