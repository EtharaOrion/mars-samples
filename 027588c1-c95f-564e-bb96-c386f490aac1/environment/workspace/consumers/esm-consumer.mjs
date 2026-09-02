import { config, combine, VERSION } from "@pkg/dual";

process.stdout.write("config.name=" + config.name + "\n");
process.stdout.write("config.ready=" + config.ready + "\n");
process.stdout.write("config.seed=" + config.seed + "\n");
process.stdout.write("combine=" + combine("alpha", "beta") + "\n");
process.stdout.write("VERSION=" + VERSION + "\n");
