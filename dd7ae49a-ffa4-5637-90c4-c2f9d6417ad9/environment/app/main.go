package main

import (
	"bufio"
	"database/sql"
	"encoding/json"
	"fmt"
	"net"
	"net/http"
	"os"
	"strconv"
	"strings"
	"sync/atomic"
	"time"

	_ "github.com/lib/pq"
)

type Order struct {
	ID          int    `json:"id"`
	Customer    string `json:"customer"`
	AmountCents int    `json:"amount_cents"`
	Status      string `json:"status"`
	Source      string `json:"source"`
}

type cacheOrder struct {
	ID          int    `json:"id"`
	Customer    string `json:"customer"`
	AmountCents int    `json:"amount_cents"`
	Status      string `json:"status"`
}

var (
	db      *sql.DB
	dbReady int32
)

func getenv(k, d string) string {
	if v := os.Getenv(k); v != "" {
		return v
	}
	return d
}

func initDB() {
	host := getenv("DB_HOST", "db")
	port := getenv("DB_PORT", "5432")
	user := getenv("DB_USER", "appuser")
	pass := getenv("DB_PASSWORD", "apppass")
	name := getenv("DB_NAME", "appdb")
	dsn := fmt.Sprintf("host=%s port=%s user=%s password=%s dbname=%s sslmode=disable connect_timeout=3", host, port, user, pass, name)
	deadline := time.Now().Add(20 * time.Second)
	for time.Now().Before(deadline) {
		d, err := sql.Open("postgres", dsn)
		if err == nil {
			if err = d.Ping(); err == nil {
				db = d
				atomic.StoreInt32(&dbReady, 1)
				return
			}
			d.Close()
		}
		time.Sleep(500 * time.Millisecond)
	}
}

func redisAddr() string {
	return getenv("REDIS_HOST", "redis") + ":" + getenv("REDIS_PORT", "6379")
}

func redisCommand(args ...string) (string, bool, error) {
	conn, err := net.DialTimeout("tcp", redisAddr(), 2*time.Second)
	if err != nil {
		return "", false, err
	}
	defer conn.Close()
	conn.SetDeadline(time.Now().Add(2 * time.Second))
	var b strings.Builder
	fmt.Fprintf(&b, "*%d\r\n", len(args))
	for _, a := range args {
		fmt.Fprintf(&b, "$%d\r\n%s\r\n", len(a), a)
	}
	if _, err = conn.Write([]byte(b.String())); err != nil {
		return "", false, err
	}
	r := bufio.NewReader(conn)
	line, err := r.ReadString('\n')
	if err != nil {
		return "", false, err
	}
	line = strings.TrimRight(line, "\r\n")
	if len(line) == 0 {
		return "", false, fmt.Errorf("empty reply")
	}
	switch line[0] {
	case '+', ':':
		return line[1:], true, nil
	case '-':
		return "", false, fmt.Errorf("redis error: %s", line[1:])
	case '$':
		n, convErr := strconv.Atoi(line[1:])
		if convErr != nil {
			return "", false, convErr
		}
		if n < 0 {
			return "", false, nil
		}
		buf := make([]byte, n+2)
		if _, err = readFull(r, buf); err != nil {
			return "", false, err
		}
		return string(buf[:n]), true, nil
	default:
		return "", false, fmt.Errorf("unexpected reply: %s", line)
	}
}

func readFull(r *bufio.Reader, buf []byte) (int, error) {
	total := 0
	for total < len(buf) {
		n, err := r.Read(buf[total:])
		total += n
		if err != nil {
			return total, err
		}
	}
	return total, nil
}

func cacheKey(id string) string { return "order:" + id }

func getCache(id string) (*Order, bool) {
	val, ok, err := redisCommand("GET", cacheKey(id))
	if err != nil || !ok {
		return nil, false
	}
	var co cacheOrder
	if json.Unmarshal([]byte(val), &co) != nil {
		return nil, false
	}
	return &Order{ID: co.ID, Customer: co.Customer, AmountCents: co.AmountCents, Status: co.Status, Source: "cache"}, true
}

func setCache(id string, o *Order) {
	co := cacheOrder{ID: o.ID, Customer: o.Customer, AmountCents: o.AmountCents, Status: o.Status}
	payload, err := json.Marshal(co)
	if err != nil {
		return
	}
	redisCommand("SETEX", cacheKey(id), "300", string(payload))
}

func writeJSON(w http.ResponseWriter, code int, v interface{}) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(code)
	json.NewEncoder(w).Encode(v)
}

func orderHandler(w http.ResponseWriter, req *http.Request) {
	idStr := strings.TrimPrefix(req.URL.Path, "/order/")
	if idStr == "" || strings.Contains(idStr, "/") {
		writeJSON(w, 400, map[string]string{"error": "bad id"})
		return
	}
	id, err := strconv.Atoi(idStr)
	if err != nil {
		writeJSON(w, 400, map[string]string{"error": "bad id"})
		return
	}
	if o, ok := getCache(idStr); ok {
		writeJSON(w, 200, o)
		return
	}
	if atomic.LoadInt32(&dbReady) == 0 || db == nil {
		writeJSON(w, 503, map[string]string{"error": "db unavailable", "source": "none"})
		return
	}
	var o Order
	row := db.QueryRow("SELECT id, customer, amount_cents, status FROM orders WHERE id = $1", id)
	if scanErr := row.Scan(&o.ID, &o.Customer, &o.AmountCents, &o.Status); scanErr != nil {
		if scanErr == sql.ErrNoRows {
			writeJSON(w, 404, map[string]string{"error": "not found"})
			return
		}
		writeJSON(w, 500, map[string]string{"error": "query failed", "source": "none"})
		return
	}
	o.Source = "db"
	setCache(idStr, &o)
	writeJSON(w, 200, o)
}

func healthHandler(w http.ResponseWriter, req *http.Request) {
	writeJSON(w, 200, map[string]string{"status": "ok"})
}

func main() {
	go initDB()
	http.HandleFunc("/health", healthHandler)
	http.HandleFunc("/order/", orderHandler)
	addr := ":" + getenv("PORT", "8080")
	if err := http.ListenAndServe(addr, nil); err != nil {
		fmt.Fprintln(os.Stderr, err)
	}
}
