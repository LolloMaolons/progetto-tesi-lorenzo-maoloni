export function saveRequests(key, requests) {
  localStorage.setItem(key, JSON.stringify(requests));
}

export function loadRequests(key, defaults) {
  const raw = localStorage.getItem(key);
  if (!raw) return defaults;
  try {
    const parsed = JSON.parse(raw);
    if (Array.isArray(parsed)) return parsed;
    return defaults;
  } catch {
    return defaults;
  }
}
