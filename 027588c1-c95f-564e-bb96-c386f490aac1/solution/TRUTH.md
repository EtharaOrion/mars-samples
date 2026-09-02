GENERATED SECTION. DO NOT HAND-EDIT.

task_slug: configure-vite-dual-esm-cjs-exports-v3
source_of_truth: solution/grounding.yaml
regenerated_by: solution/recompute.py

## The single most important insight

The ESM entry at `src/index.ts` binds one of its named exports with a top-level `await`. That is valid ES2022 ESM
and it is exactly why the naive dual-package pipelines all break. Top-level `await` cannot be lowered to synchronous
CommonJS by any transpiler: `esbuild` (which `tsup` wraps) errors out with `Top-level await is currently not
supported with the "cjs" output format`, and `tsc` with `module: commonjs` errors with TS1378 `Top-level 'await'
expressions are only allowed when the 'module' option is set to 'es2022' | 'esnext' | 'system' | 'node16' |
'nodenext' | 'preserve'`. Any working dual package must therefore route the CJS consumer through a dynamic
`import(...)` call, which returns a Promise that resolves once the ESM entry has finished awaiting its
top-level expression. The CJS entry becomes a one-line shim whose `module.exports` is that Promise, and the CJS
consumer treats the required value as a thenable and reads named bindings off the fulfilled value.

## The ideal solve, step by step

1. **Read the three observed artifacts the container captured at build time.** `/workspace/observed_build.txt`
   shows the ESM build was already run and succeeded. `/workspace/observed_esm.txt` shows the ESM consumer
   already prints the expected five lines. `/workspace/observed_cjs.txt` shows the CJS consumer fails, and the
   error tells you exactly what is missing: there is no `require` condition in the package's `exports` map.

2. **Read `/workspace/app/src/index.ts` and notice the `await` at the top of the module body.** That is the
   feature the CJS build path cannot lower. It rules out every transpiler that produces synchronous CJS output.
   It does not, however, rule out a small CJS shim whose only job is to hand a Promise back to the CJS caller.

3. **Read `/workspace/consumers/cjs-consumer.cjs` and notice `Promise.resolve(loaded).then(m => ...)`.** The
   consumer already treats the required value as a thenable. You do not need to change the consumer. You need
   the value that `require("@pkg/dual")` returns to be that thenable.

4. **Author `/workspace/app/dist/cjs/index.cjs` as the CJS shim.** One line: `module.exports = import("../esm/index.js");`
   plus a `"use strict";` prologue if you like. The dynamic `import()` call is what the verifier looks for in
   the CJS entry source; it is the mechanism that lets a CJS caller load an ESM module with top-level await.

5. **Update `/workspace/app/package.json` to add a `require` condition under `exports."."`.** Point it at
   `./dist/cjs/index.cjs`. Keep the existing `types` and `import` conditions. Keep `"type": "module"`. The
   verifier walks the `exports` map by name, resolves each condition target against `/workspace/app/`, and
   rejects anything that does not point at a real file on disk under the package root.

6. **Run the ESM build to make sure `dist/esm/` is fresh, then run both consumers.** From `/workspace/app` run
   `./node_modules/.bin/tsc -p tsconfig.esm.json`. Then run `node /workspace/consumers/esm-consumer.mjs` and
   `node /workspace/consumers/cjs-consumer.cjs` and confirm both print the five expected lines with a single
   trailing newline.

## Traps that catch agents that are not thinking carefully

- **Trap: `tsup --format cjs,esm` or `esbuild --format=cjs`.** Both wrap the same lowering path and both error
  out on the top-level await when the output format is CJS. No CJS bundle is written. Even if the tool were to
  silently emit a stub, the verifier would detect the missing dynamic import in the CJS entry source.

- **Trap: `tsc --module commonjs` (or a second tsconfig with `module: commonjs`).** TS1378 refuses to compile
  a source that uses top-level await under a CommonJS module target. No emit produced.

- **Trap: delete or rewrite the top-level `await` in `src/index.ts`.** The verifier sha256-compares `src/index.ts`
  and `src/loader.ts` against the seeded digests and rejects any byte change. The top-level await IS the pinned
  failure surface.

- **Trap: flip `"type": "module"` to `"commonjs"` to dodge the ESM semantics entirely.** The verifier hard-checks
  the `type` field is still the literal string `module` after the fix, and rejects the flipped type field even
  if both consumers happen to converge under the new type.

- **Trap: hand-author `dist/cjs/index.cjs` that returns a `Promise.resolve({config: {...}, combine: ..., VERSION: ...})`
  with hardcoded values.** The verifier reads the CJS entry file, strips comments, and requires a visible
  `import(` call. It also refuses the file if it contains any of the expected output substrings such as
  `config.name=@pkg/dual`, `combine=alpha::beta`, or `VERSION=1.0.0`. Both gates catch this shortcut.

- **Trap: point `exports.require` at `./dist/esm/index.js` directly and hope Node accepts it.** Node's CJS
  resolver refuses to `require()` an ESM module that uses top-level await; the CJS consumer exits nonzero with
  `ERR_REQUIRE_ESM`.

- **Trap: edit `/workspace/consumers/cjs-consumer.cjs` or `esm-consumer.mjs` to route around the package.json**
  **exports map (e.g. import directly from `../app/dist/esm/index.js`).** The verifier sha256-compares both
  consumer files against pinned digests. Consumer files are verifier-owned probes; editing them is rejected.

- **Trap: install `deasync` or a similar native binding to synchronously drain the Promise.** No network egress,
  and the slim base image has no C++ toolchain to build native addons.

## The one route that satisfies every checker

Author `/workspace/app/dist/cjs/index.cjs` as `"use strict"; module.exports = import("../esm/index.js");`. Rewrite
`/workspace/app/package.json` to add a `require` condition under `exports."."` pointing at `./dist/cjs/index.cjs`,
keeping the existing `types` and `import` conditions and keeping `"type": "module"`. Run the ESM build to
populate `dist/esm/`. Then confirm both consumers print the five expected lines with a single trailing newline.

### Canary tokens planted in this file
- forge_canary_a: FORGE_HOLDOUT_CANARY_3609B7D635F886C9D0DC7DCFA8A18394
- forge_canary_b_reference: FORGE_HOLDOUT_CANARY_71D9590F37529FF6569AEDFC08DA6283
