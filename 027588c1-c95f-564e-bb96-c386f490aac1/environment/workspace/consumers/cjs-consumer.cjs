"use strict";

const loaded = require("@pkg/dual");

Promise.resolve(loaded)
  .then(function (m) {
    process.stdout.write("config.name=" + m.config.name + "\n");
    process.stdout.write("config.ready=" + m.config.ready + "\n");
    process.stdout.write("config.seed=" + m.config.seed + "\n");
    process.stdout.write("combine=" + m.combine("alpha", "beta") + "\n");
    process.stdout.write("VERSION=" + m.VERSION + "\n");
  })
  .catch(function (e) {
    process.stderr.write(String((e && e.stack) || e) + "\n");
    process.exit(1);
  });
