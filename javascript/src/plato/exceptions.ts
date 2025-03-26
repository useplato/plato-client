export class PlatoClientError extends Error {
  constructor(message: string) {
    super(message);
    this.name = 'PlatoClientError';
  }
} 