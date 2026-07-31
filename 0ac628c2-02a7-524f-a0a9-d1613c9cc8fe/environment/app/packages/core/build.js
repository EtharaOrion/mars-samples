const fs = require("fs");
const path = require("path");
const dist = path.join(__dirname, "dist");
fs.mkdirSync(dist, { recursive: true });
fs.copyFileSync(path.join(__dirname, "src", "index.js"), path.join(dist, "index.js"));
