export type BlockType =
    | "profile_header" | "contact" | "social_links" | "summary" | "experience" | "project"
    | "education" | "skills" | "certifications" | "awards" | "publications" | "languages"
    | "custom_text" | "custom_list" | "divider";

export interface ResumeBlock {
    id: string;
    type: BlockType;
    title: string;
    visible: boolean;
    content: Record<string, unknown>;
    style?: Record<string, string>;
    source_ids?: string[];
}

export interface ResumeColumn { id: string; width: number; min_width: number; max_width: number; section_ids: string[]; }
export interface ResumeDocument { schema_version: 1; paper: "a4" | "letter"; pages: { id: string; rows: { id: string; columns: ResumeColumn[] }[] }[]; blocks: ResumeBlock[]; style: { font_family: string; font_size: number; accent_color: string; text_color: string; margin: number; spacing: number; density: string; }; }
export interface ResumeRevision { id: number; workspace_id: number; revision_number: number; document: ResumeDocument; content_hash: string; change_kind: string; created_at: string; }
export interface ResumeWorkspace { id: number; title: string; job_description: string; template_key: string; status: string; current_revision_id: number | null; created_at: string; updated_at: string; }
export interface ResumeTemplate { template_key: string; version: number; name: string; description: string; notes: string }

export const blockText = (block: ResumeBlock, key: string, fallback = "") => {
    const value = block.content[key];
    return typeof value === "string" ? value : fallback;
};
