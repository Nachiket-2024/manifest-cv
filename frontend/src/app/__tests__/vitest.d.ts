// ManifestCV's app tests use the same runtime matchers as MysticAuth. Keep
// this declaration app-owned so the upstream MysticAuth test setup remains
// untouched while Vitest 5 and jest-dom 7 can coexist in this workspace.
import "vitest";

declare module "vitest" {
  interface Assertion<R extends void | Promise<void> = void, T = unknown> {
    readonly not: Assertion<R, T>;
    // The matcher surface is supplied dynamically by jest-dom.
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    [matcher: string]: (...args: any[]) => any;
  }
}
