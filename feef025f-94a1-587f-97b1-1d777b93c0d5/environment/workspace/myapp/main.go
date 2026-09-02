// Package main is the myapp entrypoint. It depends on example.com/mylib,
// which is expected to be resolved locally via the `replace` directive
// in go.mod. The dependency is not fetched from any network source.
package main

import (
	"fmt"

	"example.com/mylib"
)

func main() {
	fmt.Println(mylib.Greet("world"))
	fmt.Println(mylib.Farewell("world"))
}
