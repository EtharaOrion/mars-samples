const core = require("./dist/index.js");
if (core.compute(10) !== 385) {
  console.error("core self-test failed: compute(10)=" + core.compute(10));
  process.exit(1);
}
if (core.CORE_VERSION !== "2.0.0") {
  console.error("core self-test failed: version=" + core.CORE_VERSION);
  process.exit(1);
}
console.log("core ok");
