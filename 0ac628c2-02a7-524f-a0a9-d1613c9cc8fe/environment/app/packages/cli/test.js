const { line } = require("./dist/index.js");
const want = "@app/cli: sum-of-squares(10) = 385 [core v2.0.0]";
if (line !== want) {
  console.error("cli self-test failed: " + line);
  process.exit(1);
}
console.log("cli ok");
