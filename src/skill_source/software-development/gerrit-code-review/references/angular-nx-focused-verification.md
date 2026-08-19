# Angular/Nx focused verification

Use this note when reviewing an Angular/Nx patch that changes or extracts unit-tested code.

## Do not trust the requested test list

A focused command can exit successfully while exercising fewer files than requested. In one observed Nx/Jest invocation, `nx test <project> --runTestsByPath file1 file2 file3 ...` printed all paths in the target command but Jest executed only one suite.

Verification rule:

1. Count the requested spec files.
2. Read Jest's final `Test Suites: N ...` summary.
3. Require `N` to match the intended suite count.
4. If it does not, run Jest directly with the repository's project config, for example:

   ```bash
   npx jest --config apps/<app>/jest.config.ts --runInBand path/to/a.spec.ts path/to/b.spec.ts
   ```

   Running each path separately is also acceptable.
5. Report the observed suite and test totals, not merely exit code 0.

## Layered review sequence

For a changed Angular application, prefer this evidence stack when feasible:

1. Focused changed-area suites with verified suite count.
2. Application-wide unit tests.
3. `tsc --noEmit` using the application tsconfig.
4. Application lint; distinguish changed-file findings from unrelated repository warnings.
5. Development or production build, depending on the repository's CI path.
6. `git diff --check`, exact revision read-back, and clean tracked status.

## Extracted-helper API check

Refactors often move private component logic into standalone modules. Tests may prove behavior while missing accidental API expansion. Run an unused-export check scoped to changed paths (for example `ts-prune`) and inspect symbols reported as “used in module.” Remove `export` from module-internal types/functions unless they are intentionally public.

Treat unnecessary exports as cleanup/minor severity unless the repository has a strict public API policy or the export creates a concrete compatibility risk.
