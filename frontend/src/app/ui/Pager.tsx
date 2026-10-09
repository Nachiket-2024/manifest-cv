import React from "react";
import { useTranslation } from "react-i18next";

import { Button } from "../sdk";

interface PagerProps {
    offset: number;
    limit: number;
    /** Count of rows the current page actually returned. Fewer than
     * `limit` means this is the last page (standard offset-pagination
     * heuristic, avoids needing a separate total-count endpoint). */
    rowCount: number | undefined;
    onOffsetChange: (offset: number) => void;
}

/**
 * Shared Previous/Next pager for offset-paginated list pages (Resumes,
 * Applications). Mirrors the limit/offset convention already used by the
 * inherited audit-log endpoints (see backend/app/api/audit_log_routes/).
 */
const Pager: React.FC<PagerProps> = ({ offset, limit, rowCount, onOffsetChange }) => {
    const { t } = useTranslation("app_common");
    const hasPreviousPage = offset > 0;
    const hasNextPage = rowCount !== undefined && rowCount === limit;

    if (offset === 0 && !hasNextPage) {
        // Nothing to page through. One page's worth of rows or fewer.
        return null;
    }

    return (
        <div className="mt-4 flex items-center justify-end gap-3">
            <span className="text-sm text-fg-muted">
                {t("pager.page", { n: Math.floor(offset / limit) + 1 })}
            </span>
            <Button
                size="sm"
                variant="outline"
                onClick={() => onOffsetChange(Math.max(0, offset - limit))}
                disabled={!hasPreviousPage}
            >
                {t("pager.previous")}
            </Button>
            <Button
                size="sm"
                variant="outline"
                onClick={() => onOffsetChange(offset + limit)}
                disabled={!hasNextPage}
            >
                {t("pager.next")}
            </Button>
        </div>
    );
};

export default Pager;
