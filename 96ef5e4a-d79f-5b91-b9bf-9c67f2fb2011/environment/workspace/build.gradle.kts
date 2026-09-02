// build.gradle.kts -- Kotlin DSL only. Do NOT introduce a build.gradle
// Groovy fallback file: the verifier rejects a Groovy DSL companion.
//
// This project must build on a JDK 21 toolchain (the CI infrastructure
// pins JDK 21 as the sole runner-side JVM) but emit main class bytecode
// targeting JDK 17 (major version 61), because the deployed artifacts
// run on a fleet whose oldest node still runs JDK 17. Both JDK 21 and
// JDK 17 are pre-provisioned on the container and reachable through
// the auto-detected Gradle toolchain locations.
//
// The toolchain block below is INCOMPLETE. It pins the build JVM to
// JDK 21 but does not constrain the emitted bytecode target, so a
// fresh `gradle build` compiles main classes to bytecode major
// version 65 (JDK 21) and the grader's javap invariant fails. Your
// job is to add the missing Kotlin-DSL directive that forces main
// compilation to release-target 17 while leaving the build toolchain
// on JDK 21.

plugins {
    java
}

group = "com.example"
version = "1.0.0"

repositories {
    mavenCentral()
}

dependencies {
    testImplementation("org.junit.jupiter:junit-jupiter:5.10.0")
    testRuntimeOnly("org.junit.platform:junit-platform-launcher")
}

tasks.test {
    useJUnitPlatform()
}

java {
    toolchain {
        languageVersion.set(JavaLanguageVersion.of(21))
    }
}

// FIXME: main class bytecode currently ends up as major version 65 (JDK 21).
// The grader requires build/classes/java/main/com/example/App.class to
// report `major version: 61` under `javap -v`. Add the missing Kotlin
// DSL directive here (NOT above the java { toolchain { ... } } block,
// which must keep pinning the build JVM to JDK 21).
