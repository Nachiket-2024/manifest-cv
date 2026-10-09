import { create } from "zustand";
import type { ResumeDocument } from "./resumeDocumentTypes";

interface EditorState {
    document: ResumeDocument | null;
    selectedId: string | null;
    savedRevisionId: number | null;
    dirty: boolean;
    undo: ResumeDocument[];
    redo: ResumeDocument[];
    setDocument: (document: ResumeDocument, revisionId: number | null) => void;
    update: (change: (document: ResumeDocument) => ResumeDocument) => void;
    select: (id: string | null) => void;
    undoChange: () => void;
    redoChange: () => void;
    markSaved: (revisionId: number) => void;
}

export const useResumeEditorStore = create<EditorState>((set) => ({
    document: null, selectedId: null, savedRevisionId: null, dirty: false, undo: [], redo: [],
    setDocument: (document, revisionId) => set({ document, savedRevisionId: revisionId, dirty: false, undo: [], redo: [] }),
    update: (change) => set((state) => state.document ? { document: change(state.document), undo: [...state.undo, state.document].slice(-50), redo: [], dirty: true } : state),
    select: (selectedId) => set({ selectedId }),
    undoChange: () => set((state) => { const previous = state.undo.at(-1); return previous && state.document ? { document: previous, undo: state.undo.slice(0, -1), redo: [state.document, ...state.redo].slice(0, 50), dirty: true } : state; }),
    redoChange: () => set((state) => { const next = state.redo[0]; return next && state.document ? { document: next, redo: state.redo.slice(1), undo: [...state.undo, state.document].slice(-50), dirty: true } : state; }),
    markSaved: (savedRevisionId) => set({ savedRevisionId, dirty: false, undo: [], redo: [] }),
}));
