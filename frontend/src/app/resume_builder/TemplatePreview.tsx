import React from "react";
import type { ResumeDocument, ResumeTemplate } from "./resumeDocumentTypes";

interface TemplatePreviewProps {
    template: ResumeTemplate & { document: ResumeDocument };
    compact?: boolean;
}

const TemplatePreview: React.FC<TemplatePreviewProps> = ({ template, compact = false }) => {
    const { document } = template;
    const scale = compact ? "h-52" : "h-[28rem]";
    return (
        <div
            className={`overflow-hidden rounded-lg border border-gray-200 bg-gray-100 p-3 shadow-inner dark:border-gray-700 dark:bg-gray-950 ${scale}`}
            aria-label={`${template.name} layout preview`}
        >
            <div className="mx-auto flex h-full max-w-[22rem] flex-col gap-2 overflow-hidden bg-white p-3 text-[6px] text-gray-700 dark:bg-gray-900 dark:text-gray-200" style={{ fontFamily: document.style.font_family }}>
                {document.pages.map((page, pageIndex) => (
                    <React.Fragment key={page.id}>
                        {pageIndex > 0 && <div className="my-1 border-t border-dashed border-gray-300 pt-1 text-center text-[5px] text-gray-400 dark:border-gray-700 dark:text-gray-500">Page {pageIndex + 1}</div>}
                        {page.rows.map((row) => (
                            <div key={row.id} className="grid min-h-0 gap-2" style={{ flex: page.rows.length === 1 ? 1 : undefined, gridTemplateColumns: row.columns.map((column) => `${column.width}fr`).join(" ") }}>
                                {row.columns.map((column) => (
                                    <div key={column.id} className="min-w-0 space-y-2">
                                        {column.section_ids.map((sectionId, index) => {
                                            const block = document.blocks.find((candidate) => candidate.id === sectionId);
                                            if (!block || !block.visible) return null;
                                            return (
                                                <div key={block.id} className="space-y-1">
                                                    {index === 0 && block.type === "profile_header" ? (
                                                        <div className="border-b-2 pb-2" style={{ borderColor: document.style.accent_color }}>
                                                            <div className="h-3 w-3/4 rounded" style={{ backgroundColor: document.style.accent_color }} />
                                                            <div className="mt-1 h-1.5 w-1/2 rounded bg-gray-300 dark:bg-gray-700" />
                                                        </div>
                                                    ) : (
                                                        <>
                                                            <div className="flex items-center gap-1 font-semibold uppercase tracking-wide" style={{ color: document.style.accent_color }}>
                                                                <span className="h-1 w-1 rounded-full" style={{ backgroundColor: document.style.accent_color }} />
                                                                {block.title}
                                                            </div>
                                                            <div className="space-y-1 border-t border-gray-100 pt-1 dark:border-gray-800">
                                                                <div className="h-1.5 w-full rounded bg-gray-200 dark:bg-gray-700" />
                                                                <div className="h-1.5 w-5/6 rounded bg-gray-200 dark:bg-gray-700" />
                                                                {index % 3 === 0 && <div className="h-1.5 w-2/3 rounded bg-gray-100 dark:bg-gray-800" />}
                                                            </div>
                                                        </>
                                                    )}
                                                </div>
                                            );
                                        })}
                                    </div>
                                ))}
                            </div>
                        ))}
                    </React.Fragment>
                ))}
            </div>
        </div>
    );
};

export default TemplatePreview;
