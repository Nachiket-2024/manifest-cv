import { describe, it, expect, beforeEach } from 'vitest';
import MockAdapter from 'axios-mock-adapter';
import api from '@/mystic_auth/api/axiosInstance';
import {
  listResumeTemplatesApi,
  resumeTemplatePreviewUrl,
  finalizeResumeDocumentApi,
  getFinalizedResumeDocumentApi,
  resumeDocumentDownloadUrl,
} from '@/api/document_api';

const mock = new MockAdapter(api);

beforeEach(() => {
  mock.reset();
});

describe('listResumeTemplatesApi', () => {
  it('sends a GET request to /resumes/{draftId}/templates', async () => {
    mock.onGet('/resumes/7/templates').reply(200, [{ id: 'classic', label: 'Classic' }]);

    const response = await listResumeTemplatesApi(7);

    expect(response.data).toEqual([{ id: 'classic', label: 'Classic' }]);
  });
});

describe('resumeTemplatePreviewUrl', () => {
  it('builds the preview URL from draftId, templateId, and base URL', () => {
    expect(resumeTemplatePreviewUrl(7, 'classic', 'http://localhost:8000')).toBe(
      'http://localhost:8000/resumes/7/templates/classic/preview'
    );
  });
});

describe('finalizeResumeDocumentApi', () => {
  it('sends a POST request to /resumes/{draftId}/finalize with the template id', async () => {
    mock.onPost('/resumes/7/finalize').reply((config) => {
      expect(JSON.parse(config.data)).toEqual({ template_id: 'modern' });
      return [200, { id: 1, resume_draft_id: 7, template_id: 'modern' }];
    });

    const response = await finalizeResumeDocumentApi(7, 'modern');

    expect(response.data.template_id).toBe('modern');
  });
});

describe('getFinalizedResumeDocumentApi', () => {
  it('sends a GET request to /resumes/{draftId}/finalize', async () => {
    mock.onGet('/resumes/7/finalize').reply(200, { id: 1, resume_draft_id: 7, template_id: 'classic' });

    const response = await getFinalizedResumeDocumentApi(7);

    expect(response.data.template_id).toBe('classic');
  });

  it('propagates a 404 when the resume has not been finalized yet', async () => {
    mock.onGet('/resumes/7/finalize').reply(404, { detail: "This resume hasn't been finalized yet" });

    await expect(getFinalizedResumeDocumentApi(7)).rejects.toMatchObject({ response: { status: 404 } });
  });
});

describe('resumeDocumentDownloadUrl', () => {
  it('builds the download URL from draftId and base URL', () => {
    expect(resumeDocumentDownloadUrl(7, 'http://localhost:8000')).toBe(
      'http://localhost:8000/resumes/7/finalize/download'
    );
  });
});
