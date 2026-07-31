const core = require("@app/core");

const N = 10;
const line = "@app/cli: " + core.LABEL + "(" + N + ") = " + core.compute(N) +
  " [core v" + core.CORE_VERSION + "]";

console.log(line);

module.exports = { line };
