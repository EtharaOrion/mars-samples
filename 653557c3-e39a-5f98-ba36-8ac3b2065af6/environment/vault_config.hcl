ui = false
disable_mlock = true

storage "file" {
  path = "/var/lib/vault/file"
}

listener "tcp" {
  address     = "127.0.0.1:8200"
  tls_disable = true
}

api_addr = "http://127.0.0.1:8200"
