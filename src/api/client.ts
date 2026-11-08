import { Api } from './api';

const baseUrl = import.meta.env.VITE_API_BASE_URL || '';

let csrfToken: string | null = null;
let csrfRequest: Promise<string> | null = null;

async function refreshCsrfToken(): Promise<string> {
  if (!csrfRequest) {
    csrfRequest = (async () => {
      const healthUrl = `${baseUrl.replace(/\/+$/, '')}/health`;
      const response = await fetch(healthUrl, {
        method: 'GET',
        credentials: 'include',
      });

      if (!response.ok) {
        throw new Error(`Не удалось получить CSRF-токен: ${response.status}`);
      }

      const data: { csrfToken?: string } = await response.json();

      if (!data.csrfToken) {
        throw new Error('В ответе /health отсутствует csrfToken.');
      }

      csrfToken = data.csrfToken;
      return csrfToken;
    })().finally(() => {
      csrfRequest = null;
    });
  }

  return csrfRequest;
}

export async function initializeApi(): Promise<void> {
  if (!csrfToken) {
    await refreshCsrfToken();
  }
}

const customFetch: typeof fetch = async (input, init) => {
  const requestInit: RequestInit = {
    ...init,
    credentials: 'include',
  };

  const method = (requestInit.method || 'GET').toUpperCase();
  const isUnsafeMethod = !['GET', 'HEAD', 'OPTIONS'].includes(method);

  if (!isUnsafeMethod) {
    return fetch(input, requestInit);
  }

  if (!csrfToken) {
    await refreshCsrfToken();
  }

  const sendRequest = () => {
    const headers = new Headers(requestInit.headers);
    headers.set('X-CSRFToken', csrfToken!);

    return fetch(input, {
      ...requestInit,
      headers,
    });
  };

  let response = await sendRequest();

  if (response.status === 403) {
    await refreshCsrfToken();
    response = await sendRequest();
  }

  return response;
};

export const { api } = new Api({
  baseUrl,
  customFetch,
  baseApiParams: {
    credentials: 'include',
  },
});
