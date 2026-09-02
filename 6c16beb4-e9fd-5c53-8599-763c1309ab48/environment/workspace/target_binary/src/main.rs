use std::process;

fn main() {
    let args: Vec<String> = std::env::args().collect();
    if args.len() < 3 {
        eprintln!("usage: target_binary <endpoint_for_webhook_sender> <endpoint_for_api_gateway>");
        process::exit(2);
    }
    let ep1 = &args[1];
    let ep2 = &args[2];

    let r1 = match webhook_sender::send_webhook("localhost", 8443, ep1) {
        Ok(r) => r,
        Err(e) => {
            eprintln!("webhook_sender::send_webhook failed: {}", e);
            process::exit(3);
        }
    };
    let r2 = match api_gateway::call_api("localhost", 8443, ep2) {
        Ok(r) => r,
        Err(e) => {
            eprintln!("api_gateway::call_api failed: {}", e);
            process::exit(4);
        }
    };
    print!("{}", r1);
    println!("---");
    print!("{}", r2);
}
