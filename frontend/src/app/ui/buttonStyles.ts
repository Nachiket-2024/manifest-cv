// App-local counterpart to mystic_auth/ui/styles/buttonStyles.ts, for hover
// treatments this app needs that the template doesn't already export. Kept
// separate (not editing mystic_auth's own file) for the same reason as
// app_sdk.ts, so template updates never conflict with app-specific
// additions. See docs/mystic_auth/template-usage/overview.md.

// Same "fills up" fix as mystic_auth's BRAND_OUTLINE_HOVER_PROPS
// (outline/colorPalette="brand" secondary actions), applied to a
// colorPalette="red" outline instead: an outline button's stock hover only
// lightens its already-transparent background a shade, which barely reads
// as a state change. Fills solid red on hover with white text instead (e.g.
// CareerKnowledgePage's "Start over").
export const DESTRUCTIVE_OUTLINE_HOVER_PROPS = {
    _hover: { bg: "red.500", color: "white" },
};
