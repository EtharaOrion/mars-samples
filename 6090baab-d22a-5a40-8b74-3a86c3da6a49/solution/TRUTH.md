GENERATED SECTION. DO NOT HAND-EDIT.

task_slug: fix-tsc-paths-runtime-resolver-drift-v2
source_of_truth: solution/grounding.yaml
regenerated_by: solution/recompute.py

## The single most important insight

The container built with `noEmit: true` in tsconfig, so `tsc` at build time typechecked the sources without writing
anything to `dist/`. That is why `node /workspace/app/dist/index.js` fails with `Cannot find module` on `dist/index.js`
itself: the file does not exist. The trap is that the traceback names a plausible-looking runtime-resolution failure
that pattern-matches a paths-alias or ESM-extension bug, but the actual cause is the compiler is set to skip emit.

Flipping `noEmit` off alone is not enough. The source imports `./greet.ts` and `./farewell.ts` with the `.ts` extension,
which requires `allowImportingTsExtensions: true`, which in turn requires one of `noEmit`, `emitDeclarationOnly`, or
`rewriteRelativeImportExtensions` to be set. Because `noEmit` must go away to populate `dist/`, and
`emitDeclarationOnly` produces no runnable JavaScript, only `rewriteRelativeImportExtensions: true` unblocks emit.
The last piece is `moduleResolution: bundler` paired with `module: preserve`: the verifier byte-checks that the
final `tsconfig.json` names `bundler` at the `moduleResolution` key. Other resolutions (`node`, `node10`, `node16`,
`nodenext`, `classic`) may also compile and even run under the right emit settings, but the verifier's
`T2_tsconfig_moduleResolution_bundler` gate hard-pins bundler and rejects anything else.

## The ideal solve, step by step

1. **Read the two observed artifacts the container captured at build time.** Open `/workspace/observed_tsc.txt`
   and confirm it is empty (or nearly so) with returncode 0. Open `/workspace/observed_node.txt` and confirm the
   error names `dist/index.js` itself, not any file under `dist/`. That single detail rules out the whole family
   of "paths alias didn't propagate" or "ESM needs `.js` extension" hypotheses that the naive reader reaches
   for first: those bugs fail on a nested file, not on the entry file.

2. **Read `/workspace/app/tsconfig.json` and notice `noEmit: true`.** With `noEmit: true`, `tsc` emits nothing;
   there is no `dist/` directory to run. That is the whole crash. The reason `tsc` was silent at container-build
   time is that typecheck-only succeeds when there is nothing to emit that could fail.

3. **Read `/workspace/app/src/index.ts` and notice the `.ts` extension on the two relative imports.** This is
   why `noEmit` is set: `allowImportingTsExtensions: true` requires it (or `emitDeclarationOnly`, or
   `rewriteRelativeImportExtensions`). You cannot just delete `noEmit` and keep everything else, because
   `tsc` will refuse with `TS5096`.

4. **Choose `rewriteRelativeImportExtensions: true`.** This is the only replacement for `noEmit` that produces
   a working `dist/`: it rewrites `.ts` in imports to `.js` at emit, so the runtime specifiers become
   `./greet.js` and `./farewell.js`. Node's ESM loader resolves them against the emitted files.

5. **Set `moduleResolution: bundler` and `module: preserve`.** The verifier hard-pins `moduleResolution: bundler`;
   `module: preserve` is the emit setting that pairs with it and keeps the source `import` syntax intact so the
   emitted JavaScript is valid Node ESM. The pair is documented in the TypeScript 5.4 release notes as the
   intended combination for projects that ship their `.ts` extensions through to a rewriter.

6. **Write the final `tsconfig.json`, run `./node_modules/.bin/tsc` from `/workspace/app`, and confirm.**
   `./node_modules/.bin/tsc --noEmit` prints nothing. `./node_modules/.bin/tsc` populates `dist/` with
   `index.js`, `greet.js`, and `farewell.js`. `node /workspace/app/dist/index.js` prints:

       Hello, Mars!
       Goodbye, Mars.

   followed by a single trailing newline. That is the exact byte pattern the verifier compares against.

## Traps that catch agents that are not thinking carefully

- **Trap: `pip install ts-node` / `npm install tsx` / `npm install esbuild-register`.** No network egress; the
  install fails. Even if a copy were vendored, the verifier walks `node_modules/` and rejects any of these
  packages by name. Reaching for a runtime loader is the wrong instinct here: this is a tsconfig bug, not a
  "we need a runtime shim to interpret TypeScript" bug.

- **Trap: rewrite `src/index.ts` to use `.js` extensions on the imports.** The verifier sha256-compares the
  four source files. A one-byte change is rejected. The invariant says source is untouchable; this is why.

- **Trap: hand-author `/workspace/app/dist/index.js` with the expected two-line output.** The verifier re-runs
  `./node_modules/.bin/tsc` from the agent's tsconfig before running `node`, which overwrites `dist/` with a
  fresh emit. A hand-authored `dist/index.js` is destroyed on the way to the runtime check.

- **Trap: keep `noEmit: true` and add a workaround.** With `noEmit: true` on, no dist appears, no matter what
  other option is set. The verifier `E2` gate needs `dist/index.js` to exist after `tsc` runs.

- **Trap: change `moduleResolution` to `node16` or `nodenext` because the agent has seen those "fix ESM" in
  prior repos.** With `rewriteRelativeImportExtensions: true` these do also produce a working dist and a
  passing `node` invocation. But the verifier `T2` gate byte-checks that `moduleResolution` lower-equals
  `bundler` and rejects the other three (`node10`/`node`, `node16`, `nodenext`, `classic`). This is the
  shortcut-resistance lever: the naive first pass looks obvious and scores zero.

- **Trap: strip `allowImportingTsExtensions: true` and rewrite imports in some post-emit step.** The verifier
  rejects source edits and rejects extra runtime shims. There is no post-emit step available in the sandbox
  that survives the verifier's fresh `tsc` invocation.

## The one route that satisfies every checker

Overwrite `/workspace/app/tsconfig.json` with a compilerOptions block that keeps `target: es2022`, `outDir: dist`,
`rootDir: src`, `esModuleInterop: true`, `strict: true`, and `skipLibCheck: true` from the initial file, and
changes `module` to `preserve`, `moduleResolution` to `bundler`, adds `rewriteRelativeImportExtensions: true`,
keeps `allowImportingTsExtensions: true`, and removes `noEmit: true` entirely (or sets it to false). Then run
`./node_modules/.bin/tsc` from `/workspace/app` and confirm `node /workspace/app/dist/index.js` prints the two
expected lines.

### Canary tokens planted in this file
- forge_canary_a: FORGE_HOLDOUT_CANARY_8466A644288F24876270ED67CDF455EA
- forge_canary_b_reference: FORGE_HOLDOUT_CANARY_C1125110D16C53D9F0EE7783B2019AC8
