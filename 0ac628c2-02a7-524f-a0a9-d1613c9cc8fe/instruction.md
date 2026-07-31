# Repair the pnpm monorepo

The pnpm workspace at `/app` contains two local packages, `@app/core` (a
sum-of-squares library) and `@app/cli` (a reporter that consumes it via
`workspace:*`). The repository is in a half-configured state: a recursive build
does not currently produce a correct `@app/cli` artifact, and running the built
cli either fails or reports the wrong figures. Bring the workspace configuration
to a correct, working state.

When finished, the following must all hold from `/app` after a clean build
(`pnpm install --offline` then `pnpm -r build` with the `dist/` directories
removed first): `packages/core/dist/index.js` and `packages/cli/dist/index.js`
both exist, running `node packages/cli/dist/index.js` prints exactly
`@app/cli: sum-of-squares(10) = 385 [core v2.0.0]`, and `pnpm -r test` passes.
You may only change workspace and package configuration (for example
`pnpm-workspace.yaml`, `package.json` fields, and build scripts); the package
source under each `src/` directory and the `test.js` files must remain exactly
as shipped and must pass unchanged.
