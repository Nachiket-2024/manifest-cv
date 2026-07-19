import { describe, it, expect, beforeEach } from 'vitest';
import MockAdapter from 'axios-mock-adapter';
import api from '@/api/axiosInstance';
import {
  listApplicationsApi,
  getApplicationApi,
  createApplicationApi,
  updateApplicationApi,
  deleteApplicationApi,
  applicationPdfDownloadUrl,
} from '@/api/application_api';

const mock = new MockAdapter(api);

beforeEach(() => {
  mock.reset();
});

describe('listApplicationsApi', () => {
  it('sends a GET request to /applications/', async () => {
    mock.onGet('/applications/').reply(200, []);

    const response = await listApplicationsApi();

    expect(response.status).toBe(200);
  });
});

describe('getApplicationApi', () => {
  it('sends a GET request to /applications/{id}', async () => {
    mock.onGet('/applications/42').reply(200, { id: 42 });

    const response = await getApplicationApi(42);

    expect(response.data).toEqual({ id: 42 });
  });
});

describe('createApplicationApi', () => {
  it('sends a POST request to /applications/ with the payload', async () => {
    const payload = {
      resume_draft_id: 1,
      company_name: 'Acme Corp',
      application_date: '2026-07-19',
      status: 'applied',
    };
    mock.onPost('/applications/').reply((config) => {
      expect(JSON.parse(config.data)).toEqual(payload);
      return [201, { id: 1, ...payload }];
    });

    const response = await createApplicationApi(payload);

    expect(response.status).toBe(201);
  });
});

describe('updateApplicationApi', () => {
  it('sends a PATCH request to /applications/{id} with the payload', async () => {
    mock.onPatch('/applications/42').reply((config) => {
      expect(JSON.parse(config.data)).toEqual({ status: 'interviewing' });
      return [200, { id: 42, status: 'interviewing' }];
    });

    const response = await updateApplicationApi(42, { status: 'interviewing' });

    expect(response.data.status).toBe('interviewing');
  });
});

describe('deleteApplicationApi', () => {
  it('sends a DELETE request to /applications/{id}', async () => {
    mock.onDelete('/applications/42').reply(200);

    const response = await deleteApplicationApi(42);

    expect(response.status).toBe(200);
  });
});

describe('applicationPdfDownloadUrl', () => {
  it('builds the download URL from the base URL and application id', () => {
    expect(applicationPdfDownloadUrl(42, 'http://localhost:8000')).toBe(
      'http://localhost:8000/applications/42/pdf'
    );
  });
});
