package main

//go:generate go run gen.go

import (
	"fmt"

	"example.com/greeter/mathx"
	"example.com/legacy"
)

func main() {
	fmt.Printf("%s %s v%s compute(10)=%d\n", legacy.Label(), mathx.Describe(), Version, mathx.Compute(10))
}
