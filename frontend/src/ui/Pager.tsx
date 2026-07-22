import React from "react";
import { Button, HStack, Text } from "@chakra-ui/react";

interface PagerProps {
    offset: number;
    limit: number;
    /** Count of rows the current page actually returned — fewer than
     * `limit` means this is the last page (standard offset-pagination
     * heuristic, avoids needing a separate total-count endpoint). */
    rowCount: number | undefined;
    onOffsetChange: (offset: number) => void;
}

/**
 * Shared Previous/Next pager for offset-paginated list pages (Resumes,
 * Applications) — mirrors the limit/offset convention already used by the
 * inherited audit-log endpoints (see backend/app/api/audit_log_routes/).
 */
const Pager: React.FC<PagerProps> = ({ offset, limit, rowCount, onOffsetChange }) => {
    const hasPreviousPage = offset > 0;
    const hasNextPage = rowCount !== undefined && rowCount === limit;

    if (offset === 0 && !hasNextPage) {
        // Nothing to page through — one page's worth of rows or fewer.
        return null;
    }

    return (
        <HStack justify="flex-end" gap={3} mt={4}>
            <Text color="fg.muted" fontSize="sm">
                Page {Math.floor(offset / limit) + 1}
            </Text>
            <Button
                size="sm"
                variant="outline"
                onClick={() => onOffsetChange(Math.max(0, offset - limit))}
                disabled={!hasPreviousPage}
            >
                Previous
            </Button>
            <Button
                size="sm"
                variant="outline"
                onClick={() => onOffsetChange(offset + limit)}
                disabled={!hasNextPage}
            >
                Next
            </Button>
        </HStack>
    );
};

export default Pager;
