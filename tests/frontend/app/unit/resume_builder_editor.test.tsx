import { beforeEach, describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useResumeEditorStore } from "@app/resume_builder/useResumeEditorStore";
import type { ResumeDocument } from "@app/resume_builder/resumeDocumentTypes";
import { ResumeCanvas } from "@app/resume_builder/ResumeCanvas";

const document: ResumeDocument = {
    schema_version: 1,
    paper: "a4",
    pages: [{ id: "page-1", rows: [{ id: "row-1", columns: [{ id: "main", width: 1, min_width: 1, max_width: 1, section_ids: ["summary"] }] }] }],
    blocks: [{ id: "summary", type: "summary", title: "Summary", visible: true, content: { text: "Original" } }],
    style: { font_family: "inter", font_size: 10, accent_color: "#2563eb", text_color: "#1f2937", margin: 0.6, spacing: 1, density: "comfortable" },
};

describe("resume editor store", () => {
    beforeEach(() => useResumeEditorStore.getState().setDocument(document, 1));

    it("tracks undo and redo for document edits", () => {
        const store = useResumeEditorStore.getState();
        store.update((current) => ({ ...current, blocks: [{ ...current.blocks[0], content: { text: "Changed" } }] }));
        expect(useResumeEditorStore.getState().dirty).toBe(true);

        useResumeEditorStore.getState().undoChange();
        expect(useResumeEditorStore.getState().document?.blocks[0].content.text).toBe("Original");
        useResumeEditorStore.getState().redoChange();
        expect(useResumeEditorStore.getState().document?.blocks[0].content.text).toBe("Changed");
    });
});

describe("resume canvas controls", () => {
    it("exposes keyboard friendly movement and column resize controls", async () => {
        const user = userEvent.setup();
        const onMove = vi.fn();
        const onResize = vi.fn();
        render(<ResumeCanvas document={{ ...document, pages: [{ ...document.pages[0], rows: [{ ...document.pages[0].rows[0], columns: [{ ...document.pages[0].rows[0].columns[0], id: "main", width: 0.7, min_width: 0.5, max_width: 0.8 }, { id: "side", width: 0.3, min_width: 0.2, max_width: 0.5, section_ids: [] }] }] }], blocks: [{ ...document.blocks[0], title: "Summary" }] }} selectedId="summary" onSelect={vi.fn()} onMove={onMove} onDrop={vi.fn()} onResize={onResize} />);

        await user.click(screen.getByRole("button", { name: "Move Summary down" }));
        expect(onMove).toHaveBeenCalledWith("summary", "down");

        await user.click(screen.getByRole("button", { name: "Move Summary right" }));
        expect(onMove).toHaveBeenCalledWith("summary", "right");

        const resize = screen.getByRole("slider", { name: "Resize main column" });
        fireEvent.change(resize, { target: { value: "75" } });
        expect(onResize).toHaveBeenCalled();
    });
});
