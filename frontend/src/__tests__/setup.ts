// frontend/src/__tests__/setup.ts
// The "/vitest" entry point (rather than the bare package) augments
// Vitest's own `expect`/Assertion types with jest-dom's matchers —
// the generic entry point targets Jest's types instead, which left
// `.not` and other chained matchers untyped under Vitest.
import "@testing-library/jest-dom/vitest";
