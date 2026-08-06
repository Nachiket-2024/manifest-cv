import React from "react";
import { Button, HStack, Text } from "@chakra-ui/react";

import { SECONDARY_BUTTON_PROPS } from "../../mystic_auth/ui/styles/buttonStyles";

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
    const hasPreviousPage = offset > 0;
    const hasNextPage = rowCount !== undefined && rowCount === limit;

    if (offset === 0 && !hasNextPage) {
        // Nothing to page through. One page's worth of rows or fewer.
        return null;
    }

    return (
        <HStack justify="flex-end" gap={3} mt={4}>
            <Text color="fg.muted" fontSize="sm">
                Page {Math.floor(offset / limit) + 1}
            </Text>
            <Button
                size="sm"
                {...SECONDARY_BUTTON_PROPS}
                onClick={() => onOffsetChange(Math.max(0, offset - limit))}
                disabled={!hasPreviousPage}
            >
                Previous
            </Button>
            <Button
                size="sm"
                {...SECONDARY_BUTTON_PROPS}
                onClick={() => onOffsetChange(offset + limit)}
                disabled={!hasNextPage}
            >
                Next
            </Button>
        </HStack>
    );
};

export default Pager;
