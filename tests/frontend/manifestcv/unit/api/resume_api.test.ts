import { describe, it, expect, beforeEach } from 'vitest';
import MockAdapter from 'axios-mock-adapter';
import api from '@/mystic_auth/api/axiosInstance';
import {
  listResumeDraftsApi,
  getResumeDraftApi,
  createResumeDraftApi,
  updateResumeDraftApi,
  approveResumeDraftApi,
  deleteResumeDraftApi,
} from '@/api/resume_api';

const mock = new MockAdapter(api);

beforeEach(() => {
  mock.reset();
});

describe('listResumeDraftsApi', () => {
  it('sends a GET request to /resumes/', async () => {
    mock.onGet('/resumes/').reply(200, []);

    const response = await listResumeDraftsApi();

    expect(response.status).toBe(200);
  });
});

describe('getResumeDraftApi', () => {
  it('sends a GET request to /resumes/{id}', async () => {
    mock.onGet('/resumes/7').reply(200, { id: 7 });

    const response = await getResumeDraftApi(7);

    expect(response.data).toEqual({ id: 7 });
  });
});

describe('createResumeDraftApi', () => {
  it('sends a POST request to /resumes/ with the job description', async () => {
    mock.onPost('/resumes/').reply((config) => {
      expect(JSON.parse(config.data)).toEqual({ job_description: 'Backend engineer' });
      return [201, { id: 7, job_description: 'Backend engineer', status: 'draft' }];
    });

    const response = await createResumeDraftApi({ job_description: 'Backend engineer' });

    expect(response.status).toBe(201);
  });
});

describe('updateResumeDraftApi', () => {
  it('sends a PUT request to /resumes/{id} with the payload', async () => {
    mock.onPut('/resumes/7').reply((config) => {
      expect(JSON.parse(config.data)).toEqual({ refinement_prompt: 'Make it concise' });
      return [200, { id: 7, resume_content: '# Refined' }];
    });

    const response = await updateResumeDraftApi(7, { refinement_prompt: 'Make it concise' });

    expect(response.data.resume_content).toBe('# Refined');
  });
});

describe('approveResumeDraftApi', () => {
  it('sends a POST request to /resumes/{id}/approve', async () => {
    mock.onPost('/resumes/7/approve').reply(200, { id: 7, status: 'approved' });

    const response = await approveResumeDraftApi(7);

    expect(response.data.status).toBe('approved');
  });
});

describe('deleteResumeDraftApi', () => {
  it('sends a DELETE request to /resumes/{id}', async () => {
    mock.onDelete('/resumes/7').reply(200);

    const response = await deleteResumeDraftApi(7);

    expect(response.status).toBe(200);
  });
});
