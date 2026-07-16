export class WebhookError extends Error {
  constructor(message: string) {
    super(message);
    this.name = 'WebhookError';
  }
}

export class WebhookHttpError extends WebhookError {
  constructor(
    message: string,
    public readonly statusCode: number,
    public readonly body: string
  ) {
    super(message);
    this.name = 'WebhookHttpError';
  }
}

export class WebhookConnectionError extends WebhookError {
  constructor(
    message: string,
    public readonly code: string
  ) {
    super(message);
    this.name = 'WebhookConnectionError';
  }
}
