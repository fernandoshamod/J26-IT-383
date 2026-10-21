export async function api(path, options) {
  const response = await fetch(path, options);
  const body = await response.json().catch(() => ({}));
  if (!response.ok) {
    const details = body.detail;
    const message = Array.isArray(details)
      ? details.map((item) => item.msg || String(item)).join('; ')
      : typeof details === 'string' ? details : 'Request failed with HTTP ' + response.status;
    throw new Error(message);
  }
  return body;
}

export const getLocations = () => api('/api/locations');

export const generateDynamic = (event) => api('/api/packages/generate-dynamic', {
  method: 'POST', headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify(event),
});

export const validateDynamic = (event, pkg) => api('/api/feasibility/validate-dynamic', {
  method: 'POST', headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ event, package_options: pkg.package_options }),
});

