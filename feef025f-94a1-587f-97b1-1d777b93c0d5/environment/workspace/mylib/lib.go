// Package mylib is a tiny greeting helper that the myapp binary and its
// tests link against via a local `replace` directive. It has no
// external dependencies so the whole project compiles offline.
package mylib

import "fmt"

// Greet returns a greeting addressed to name.
func Greet(name string) string {
	return fmt.Sprintf("Hello, %s", name)
}

// Farewell returns a farewell addressed to name.
func Farewell(name string) string {
	return fmt.Sprintf("Goodbye, %s", name)
}
