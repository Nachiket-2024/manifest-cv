import { describe, it, expect, beforeEach } from 'vitest';
import MockAdapter from 'axios-mock-adapter';
import api from '@/api/axiosInstance';
import { oauth2LoginGoogleApi, oauth2CallbackGoogleApi } from '@/api/auth_api';

const mock = new MockAdapter(api);

// Note: the actual Google login flow in the app (OAuth2LoginButton.tsx)
// does a full-page `window.location.href` redirect straight to the
// backend's /auth/oauth2/login/google route, and the backend's own
// callback redirects the browser directly to the dashboard afterwards —
// neither of these two functions is currently called from any component,
// since a full OAuth2 redirect can't be done via an XHR/fetch call. They're
// tested here purely as API-layer functions (correct method/URL/params),
// in case a future flow needs to call them programmatically.
describe('oauth2LoginGoogleApi', () => {
  beforeEach(() => {
    mock.reset();
  });

  it('should send GET request to /auth/oauth2/login/google', async () => {
    mock.onGet('/auth/oauth2/login/google').reply(200, {});

    const response = await oauth2LoginGoogleApi();
    expect(response.status).toBe(200);
  });
});

describe('oauth2CallbackGoogleApi', () => {
  beforeEach(() => {
    mock.reset();
  });

  it('should send GET request to /auth/oauth2/callback/google with the code as a query param', async () => {
    mock.onGet('/auth/oauth2/callback/google').reply((config) => {
      expect(config.params).toEqual({ code: 'google-auth-code-abc' });
      return [200, { message: 'Login successful' }];
    });

    await oauth2CallbackGoogleApi('google-auth-code-abc');
  });

  it('should reject when Google reports an unverified email', async () => {
    mock.onGet('/auth/oauth2/callback/google').reply(400, { error: 'Unverified Google email' });

    await expect(oauth2CallbackGoogleApi('bad-code')).rejects.toMatchObject({
      response: { status: 400 },
    });
  });
});
