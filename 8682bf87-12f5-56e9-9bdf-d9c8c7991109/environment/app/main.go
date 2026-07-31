package main

import (
	"bufio"
	"encoding/json"
	"net/http"
	"os"
	"strconv"
)

const tablePath = "/app/data/table.txt"

func loadTable() []int {
	vals := []int{}
	f, err := os.Open(tablePath)
	if err != nil {
		return vals
	}
	defer f.Close()
	sc := bufio.NewScanner(f)
	for sc.Scan() {
		line := sc.Text()
		if line == "" {
			continue
		}
		n, err := strconv.Atoi(line)
		if err != nil {
			continue
		}
		vals = append(vals, n)
	}
	return vals
}

func main() {
	http.HandleFunc("/health", func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "application/json")
		json.NewEncoder(w).Encode(map[string]string{"status": "ok"})
	})
	http.HandleFunc("/compute", func(w http.ResponseWriter, r *http.Request) {
		k, _ := strconv.Atoi(r.URL.Query().Get("n"))
		table := loadTable()
		sum := 0
		for i := 0; i < k && i < len(table); i++ {
			sum += table[i]
		}
		w.Header().Set("Content-Type", "application/json")
		json.NewEncoder(w).Encode(map[string]int{"result": sum})
	})
	_ = http.ListenAndServe(":8000", nil)
}
