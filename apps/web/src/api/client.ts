export const apiClient = async <T>(
  endpoint: string,
  options?: RequestInit
): Promise<T> => {
  const url = `/api/v1${endpoint}`;
  const response = await fetch(url, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...options?.headers,
    },
  });

  if (!response.ok) {
    const errorBody = await response.text().catch(() => '');
    throw new Error(`API Error: ${response.status} - ${errorBody || response.statusText}`);
  }

  // Handle 204 No Content or empty responses
  if (response.status === 204) return {} as T;
  const text = await response.text();
  if (!text) return {} as T;

  return JSON.parse(text) as T;
};
