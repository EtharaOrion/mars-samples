use std::io::{Read, Write};
use std::net::TcpStream;
use std::sync::Arc;

pub fn send_webhook(host: &str, port: u16, path: &str) -> Result<String, Box<dyn std::error::Error>> {
    let mut root_store = rustls::RootCertStore::empty();
    let ca_pem = std::fs::read("/srv/https-mock/certs/ca.pem")?;
    let mut reader = ca_pem.as_slice();
    for cert in rustls_pemfile::certs(&mut reader) {
        root_store.add(cert?)?;
    }

    let config = rustls::ClientConfig::builder()
        .with_root_certificates(root_store)
        .with_no_client_auth();

    let server_name = rustls::pki_types::ServerName::try_from(host.to_string())?;
    let mut conn = rustls::ClientConnection::new(Arc::new(config), server_name)?;
    let mut sock = TcpStream::connect((host, port))?;
    let mut tls = rustls::Stream::new(&mut conn, &mut sock);
    let req = format!("GET {} HTTP/1.0\r\nHost: {}\r\nConnection: close\r\n\r\n", path, host);
    tls.write_all(req.as_bytes())?;
    let mut resp = String::new();
    tls.read_to_string(&mut resp)?;
    let body = resp.split("\r\n\r\n").nth(1).unwrap_or("").to_string();
    Ok(body)
}
