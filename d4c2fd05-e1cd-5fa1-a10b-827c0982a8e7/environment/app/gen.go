//go:build ignore

package main

import "os"

func main() {
	content := "package main\n\nconst Version = \"1.4.2\"\n"
	_ = os.WriteFile("version_gen.go", []byte(content), 0644)
}
