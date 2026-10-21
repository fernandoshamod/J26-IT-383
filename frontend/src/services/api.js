export async function api(path, options) {
  const response = await fetch(path, options);
  const body = await response.json().catch(() => ({}));
  if (!response.ok) {
    const details = body.detail;
    const message = Array.isArray(details)
      ? details.map((item) => item.msg || String(item)).join('; ')
      : typeof details === 'string' ? details : 'Request failed with HTTP ' + response.status;
    const error = new Error(message);
    error.status = response.status;
    throw error;
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
export const getSavedEvents = () => api('/api/events');
export const createSavedEvent = (event) => api('/api/events', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(event) });
export const updateSavedEvent = (id, event) => api('/api/events/' + encodeURIComponent(id), { method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(event) });
export const deleteSavedEvent = (id) => api('/api/events/' + encodeURIComponent(id), { method: 'DELETE' });

export const getAdminSummary = () => api('/api/admin/summary');
export const getAdminVendors = (params = {}) => api(`/api/admin/vendors?${new URLSearchParams(params)}`);
export const getAdminServiceOptions = (params = {}) => api(`/api/admin/service-options?${new URLSearchParams(params)}`);
export const getVendorDashboard = () => api('/api/vendor-demo/dashboard');
export const getVendorProfile = () => api('/api/vendor-demo/profile');
export const updateVendorProfile = (profile) => api('/api/vendor-demo/profile', { method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(profile) });
export const getVendorServices = () => api('/api/vendor-demo/services');
export const createVendorService = (service) => api('/api/vendor-demo/services', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(service) });
export const updateVendorService = (id, service) => api('/api/vendor-demo/services/' + encodeURIComponent(id), { method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(service) });
export const deleteVendorService = (id) => api('/api/vendor-demo/services/' + encodeURIComponent(id), { method: 'DELETE' });
export const getVendorAvailability = () => api('/api/vendor-demo/availability');
export const createVendorAvailability = (record) => api('/api/vendor-demo/availability', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(record) });
export const updateVendorAvailability = (id, record) => api('/api/vendor-demo/availability/' + encodeURIComponent(id), { method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(record) });
export const deleteVendorAvailability = (id) => api('/api/vendor-demo/availability/' + encodeURIComponent(id), { method: 'DELETE' });
