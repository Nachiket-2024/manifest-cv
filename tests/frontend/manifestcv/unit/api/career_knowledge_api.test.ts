import { describe, it, expect, beforeEach } from 'vitest';
import MockAdapter from 'axios-mock-adapter';
import api from '@/api/axiosInstance';
import {
  getMyCareerKnowledgeBaseApi,
  createCareerKnowledgeBaseApi,
  updateCareerKnowledgeBaseApi,
  deleteCareerKnowledgeBaseApi,
} from '@/api/career_knowledge_api';

const mock = new MockAdapter(api);

beforeEach(() => {
  mock.reset();
});

describe('getMyCareerKnowledgeBaseApi', () => {
  it('sends a GET request to /career-knowledge/', async () => {
    mock.onGet('/career-knowledge/').reply(200, { id: 1, content: '# KB' });

    const response = await getMyCareerKnowledgeBaseApi();

    expect(response.data.content).toBe('# KB');
  });

  it('propagates a 404 when the caller has no knowledge base yet', async () => {
    mock.onGet('/career-knowledge/').reply(404, { detail: 'Not found' });

    await expect(getMyCareerKnowledgeBaseApi()).rejects.toMatchObject({ response: { status: 404 } });
  });
});

describe('createCareerKnowledgeBaseApi', () => {
  it('sends a POST request to /career-knowledge/ with raw_input', async () => {
    mock.onPost('/career-knowledge/').reply((config) => {
      expect(JSON.parse(config.data)).toEqual({ raw_input: 'Raw dump.' });
      return [201, { id: 1, raw_input: 'Raw dump.', content: '# Structured' }];
    });

    const response = await createCareerKnowledgeBaseApi({ raw_input: 'Raw dump.' });

    expect(response.status).toBe(201);
  });
});

describe('updateCareerKnowledgeBaseApi', () => {
  it('sends a PUT request to /career-knowledge/ with the payload', async () => {
    mock.onPut('/career-knowledge/').reply((config) => {
      expect(JSON.parse(config.data)).toEqual({ content: '# Hand-edited' });
      return [200, { id: 1, content: '# Hand-edited' }];
    });

    const response = await updateCareerKnowledgeBaseApi({ content: '# Hand-edited' });

    expect(response.data.content).toBe('# Hand-edited');
  });
});

describe('deleteCareerKnowledgeBaseApi', () => {
  it('sends a DELETE request to /career-knowledge/', async () => {
    mock.onDelete('/career-knowledge/').reply(200);

    const response = await deleteCareerKnowledgeBaseApi();

    expect(response.status).toBe(200);
  });
});
