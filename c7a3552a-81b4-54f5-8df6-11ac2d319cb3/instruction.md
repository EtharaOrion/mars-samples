# Make the Gradle build produce a correct, runnable application

A multi-module Gradle project lives at `/app`: a `core` library module and an
`app` module that depends on it, wired together by `settings.gradle`,
`build.gradle`, `core/build.gradle`, `app/build.gradle`, and `gradle.properties`.
The build must run completely offline — every Gradle component and dependency is
already cached in the image, so build with `gradle --offline` (do not rely on
network access). Right now the build is misconfigured: a clean
`gradle --offline build` from `/app` does not yield a correct application.

Repair the build configuration so that `gradle --offline build` succeeds and the
executable jar it produces at `app/build/libs/app.jar` runs the real application
entrypoint. When that jar is run with `java -jar app/build/libs/app.jar`, it must
print exactly this single line to standard output:

    widget-core checksum=6562704

The project's JUnit test suite must also compile and pass as part of the build.
Confine your changes to the Gradle build configuration files (for example
`settings.gradle`, `build.gradle`, `core/build.gradle`, `app/build.gradle`,
`gradle.properties`); the Java sources and test sources under `core/src` and
`app/src` must remain exactly as shipped, byte for byte.
