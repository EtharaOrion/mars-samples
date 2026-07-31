package main

import (
	"fmt"

	"example.com/monorepo/libs/mathx"
	"example.com/monorepo/libs/report"
)

func main() {
	xs := []int{3, 7, 11, 13}
	fmt.Printf("app total=%d %s\n", mathx.Sum(xs), report.Render(xs))
}
