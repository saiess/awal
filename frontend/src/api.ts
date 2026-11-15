export class ApiError extends Error {
  readonly status: number;
  constructor(message: string, status: number) {
    super(message);
    this.status = status;
  }
}

export async function api<T>(path: string, options: RequestInit = {}): Promise<T> {
  const response = await fetch(path, options);
  if (!response.ok) {
    let message = response.status === 502
      ? 'The local Python server is unavailable. Run .\\dev from the project folder and keep its terminal open, then refresh.'
      : `Request failed (${response.status})`;
    try {
      const body: { detail?: string | Array<{ msg: string }> } = await response.json();
      if (typeof body.detail === 'string') message = body.detail;
      else if (Array.isArray(body.detail)) message = body.detail.map(item => item.msg).join('; ');
    } catch { /* Preserve the HTTP error if the server did not return JSON. */ }
    throw new ApiError(message, response.status);
  }
  return response.json() as Promise<T>;
}

export function jsonRequest<T>(path: string, method: 'POST' | 'PATCH', body: unknown): Promise<T> {
  return api<T>(path, { method, headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) });
}

export function errorMessage(error: unknown): string {
  return error instanceof Error ? error.message : 'The operation could not be completed.';
}
