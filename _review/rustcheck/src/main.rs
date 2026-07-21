use regex::Regex;

fn main() {
    let schema: serde_json::Value = serde_json::from_str(
        &std::fs::read_to_string("../../source/schemas/shopping/ap2_mandate.json").unwrap(),
    )
    .unwrap();
    let pat = schema["$defs"]["checkout_mandate"]["pattern"].as_str().unwrap();
    let re = Regex::new(pat).expect("pattern must compile in rust regex crate");
    let vectors: serde_json::Value =
        serde_json::from_str(&std::fs::read_to_string("../vectors.json").unwrap()).unwrap();
    let mut fails = 0;
    for (group, expected) in [("expect_accept", true), ("expect_reject", false)] {
        for v in vectors[group].as_array().unwrap() {
            let name = v[0].as_str().unwrap();
            let s = v[1].as_str().unwrap();
            let got = re.is_match(s);
            if got != expected {
                fails += 1;
                println!("FAIL [{}] {}: {:?} -> {}", group, name, s, got);
            }
        }
    }
    if fails == 0 {
        println!("accept/reject tables: ALL PASS (rust regex 1.12.2)");
    } else {
        println!("{} FAILURES (rust)", fails);
    }
    for v in vectors["questionable"].as_array().unwrap() {
        println!(
            "Q: {}: {:?} -> {}",
            v[0].as_str().unwrap(),
            v[1].as_str().unwrap(),
            if re.is_match(v[1].as_str().unwrap()) { "ACCEPT" } else { "reject" }
        );
    }
    for s in ["a.b.c~\n", "a.b.c\n", "a.b.c~d~\n"] {
        println!("NEWLINE rust: {:?} -> {}", s, re.is_match(s));
    }
}
