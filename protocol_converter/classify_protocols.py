#!/usr/bin/env python3
"""
Classify protocols into common/specialized/non_bio using Claude API (via gpugeek proxy).

Reads protocol names from success.txt, extracts README descriptions,
and uses Claude to classify each protocol.

Usage:
    python classify_protocols.py              # Round 1 only (three-way classification)
    python classify_protocols.py sub-classify  # Round 2 only (sub-classify common protocols)
    python classify_protocols.py all           # Both rounds
"""

import json
import os
import re
import sys
import time
import urllib.request

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SUCCESS_LIST = os.path.join(SCRIPT_DIR, "success.txt")
ORIGINAL_DIR = os.path.join(SCRIPT_DIR, "original")
OUTPUT_LIST = os.path.join(SCRIPT_DIR, "common_protocols.txt")
OUTPUT_JSON = os.path.join(SCRIPT_DIR, "classification_results.json")
CHECKPOINT_FILE = os.path.join(SCRIPT_DIR, "classification_checkpoint.json")
SUB_CHECKPOINT_FILE = os.path.join(SCRIPT_DIR, "sub_classification_checkpoint.json")

API_KEY = "00y7btgbzivf6w01000dgvds492xv5vu00t8sj3j"
API_URL = "https://api.gpugeek.com/predictions"
MODEL = "Vendor2/Claude-4.5-Sonnet"
BATCH_SIZE = 20
MAX_RETRIES = 5

SUB_CATEGORIES = [
    "PCR",
    "ELISA",
    "DNA_extraction",
    "RNA_extraction",
    "NGS_library_prep",
    "serial_dilution",
    "normalization",
    "plate_replication",
    "sample_transfer",
    "cell_culture",
    "protein_purification",
    "bead_cleanup",
    "other_common",
]


def parse_readme(protocol_name):
    """Extract title, categories, and description from a protocol's README.md."""
    readme_path = os.path.join(ORIGINAL_DIR, protocol_name, "README.md")
    if not os.path.exists(readme_path):
        return None

    with open(readme_path, "r", encoding="utf-8", errors="replace") as f:
        content = f.read()

    title = ""
    categories = ""
    description = ""

    m = re.search(r"^# (.+)$", content, re.MULTILINE)
    if m:
        title = m.group(1).strip()

    m = re.search(
        r"## Categories\s*\n(.*?)(?=\n## |\n---|\Z)", content, re.DOTALL
    )
    if m:
        categories = m.group(1).strip()

    m = re.search(
        r"## Description\s*\n(.*?)(?=\n---|\n## |\Z)", content, re.DOTALL
    )
    if m:
        description = m.group(1).strip()[:500]

    return {
        "title": title,
        "categories": categories,
        "description": description,
    }


def build_prompt(batch):
    """Build the classification prompt for a batch of protocols."""
    lines = []
    for item in batch:
        info = item["info"]
        lines.append(
            f"[{item['name']}]\n"
            f"Title: {info['title']}\n"
            f"Categories: {info['categories']}\n"
            f"Description: {info['description']}\n"
        )

    protocols_text = "\n".join(lines)

    prompt = f"""You are classifying Opentrons OT-2 liquid handling robot protocols.

For each protocol below, classify it into exactly ONE category:

- "common": Common biology lab experiments suitable for testing liquid handling robots. Examples: PCR prep, DNA/RNA extraction, ELISA, serial dilution, NGS library prep, normalization, pooling, plate replication, sample plating, cell culture, protein purification, bead cleanup, library pooling.
- "specialized": Real biology experiments but too vendor-specific or niche for general testing. Examples: protocols tied to a very specific commercial kit with unusual steps, highly specialized clinical workflows.
- "non_bio": Not a real biology experiment. Examples: generic liquid transfer demos, hardware test protocols, calibration, toy/demo protocols.

IMPORTANT: The "name" field in your response must be the exact protocol code shown in square brackets (e.g. [zymo-rna-extraction] → "name": "zymo-rna-extraction"). Do NOT use the README title.
IMPORTANT: The "reason" field MUST be written in Chinese (中文).

Respond with ONLY a JSON array, one object per protocol, in the same order as input:
[
  {{"name": "protocol_code", "classification": "common|specialized|non_bio", "reason": "中文分类理由"}}
]

No markdown fences, no extra text. Just the JSON array.

Protocols to classify:

{protocols_text}"""
    return prompt


def build_sub_prompt(batch):
    """Build the sub-classification prompt for common protocols."""
    lines = []
    for item in batch:
        info = item.get("info")
        if info:
            lines.append(
                f"[{item['name']}]\n"
                f"Title: {info['title']}\n"
                f"Categories: {info['categories']}\n"
                f"Description: {info['description']}\n"
            )
        else:
            lines.append(
                f"[{item['name']}]\n"
                f"Reason: {item.get('reason', '')}\n"
            )

    protocols_text = "\n".join(lines)

    sub_cats_str = ", ".join(SUB_CATEGORIES)

    prompt = f"""You are further sub-classifying common biology protocols that run on the Opentrons OT-2 liquid handling robot.

All protocols below have already been classified as "common". Now assign each one to exactly ONE sub-category AND decide if it is a "core" protocol.

Sub-categories (pick exactly one):
{sub_cats_str}

Category descriptions:
- PCR: PCR preparation, PCR amplification, qPCR setup
- ELISA: Enzyme-linked immunosorbent assay protocols
- DNA_extraction: DNA purification/extraction from various sources
- RNA_extraction: RNA purification/extraction, including viral RNA
- NGS_library_prep: Next-generation sequencing library preparation (Illumina, Nextera, etc.)
- serial_dilution: Serial dilution protocols
- normalization: Concentration normalization, library normalization
- plate_replication: Plate-to-plate transfers, stamp/replicate protocols
- sample_transfer: General sample transfers, cherry-picking, pooling, aliquoting
- cell_culture: Cell seeding, media exchange, cell-based assays
- protein_purification: Protein purification, His-tag purification, immunoprecipitation
- bead_cleanup: Magnetic bead cleanup (SPRI, AMPure, etc.)
- other_common: Common protocols that don't fit the above categories

Core protocol definition:
- "is_core": true means the protocol is a generic, standard implementation of its sub-category, NOT tied to a specific commercial kit or brand, and could serve as a representative example for that experiment type.
- "is_core": false means the protocol is tied to a specific vendor kit or is a variant/niche implementation.

IMPORTANT: The "name" field must be the exact protocol code shown in square brackets.
IMPORTANT: The "sub_reason" field MUST be written in Chinese (中文).

Respond with ONLY a JSON array, one object per protocol, in the same order as input:
[
  {{"name": "protocol_code", "sub_category": "one_of_the_sub_categories", "is_core": true|false, "sub_reason": "中文子分类理由"}}
]

No markdown fences, no extra text. Just the JSON array.

Protocols to sub-classify:

{protocols_text}"""
    return prompt


def call_llm(prompt, max_tokens=4000, temperature=0):
    """Call Claude API (via gpugeek proxy) and return the text response."""
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json",
        "Stream": "true",
    }
    data = {
        "model": MODEL,
        "input": {
            "max_tokens": max_tokens,
            "prompt": prompt,
            "temperature": temperature,
        },
    }

    for attempt in range(MAX_RETRIES):
        try:
            body = json.dumps(data).encode("utf-8")
            req = urllib.request.Request(API_URL, data=body, headers=headers, method="POST")
            with urllib.request.urlopen(req, timeout=180) as resp:
                status_code = resp.getcode()
                if status_code != 200:
                    err_body = resp.read(512).decode("utf-8", errors="replace")
                    raise Exception(f"API error {status_code}: {err_body[:200]}")

                # Response is NDJSON (newline-delimited JSON objects), each with
                # an "output" array containing text chunks. Read inside `with`
                # block while the connection is still open.
                full_text = ""
                for raw_line in resp:
                    if not raw_line:
                        continue
                    decoded = raw_line.decode("utf-8").strip()
                    if not decoded:
                        continue
                    if decoded.startswith("data:"):
                        decoded = decoded[len("data:"):].strip()
                    try:
                        obj = json.loads(decoded)
                        for t in obj.get("output", []):
                            if t:
                                full_text += t
                    except json.JSONDecodeError:
                        pass
            return full_text
        except Exception as e:
            print(f"  Error: {e}, retrying in 3s (attempt {attempt+1}/{MAX_RETRIES})...")
            if attempt < MAX_RETRIES - 1:
                time.sleep(3)
            else:
                raise


def _extract_json_array(text):
    """Robustly extract the first JSON array from LLM response text.

    Handles: markdown fences, leading prose, trailing extra data,
    and truncated trailing elements.
    """
    text = text.strip()

    # Strip markdown code fences
    if "```" in text:
        m = re.search(r"```(?:json)?\s*\n?(.*?)```", text, re.DOTALL)
        if m:
            text = m.group(1).strip()
        else:
            # Opening fence but no closing fence (truncated)
            text = re.sub(r"^```(?:json)?\s*\n?", "", text)

    # Find the first '[' — skip any leading prose
    start = text.find("[")
    if start == -1:
        raise json.JSONDecodeError("No JSON array found", text, 0)
    text = text[start:]

    # Try parsing directly first
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Find the matching ']' by brace counting, tolerating trailing junk
    depth = 0
    in_string = False
    escape = False
    end = -1
    for i, ch in enumerate(text):
        if escape:
            escape = False
            continue
        if ch == '\\' and in_string:
            escape = True
            continue
        if ch == '"' and not escape:
            in_string = not in_string
            continue
        if in_string:
            continue
        if ch == '[':
            depth += 1
        elif ch == ']':
            depth -= 1
            if depth == 0:
                end = i
                break

    if end > 0:
        try:
            return json.loads(text[:end + 1])
        except json.JSONDecodeError:
            pass

    # Last resort: find the last ']' and try to parse up to it
    last_bracket = text.rfind("]")
    if last_bracket > 0:
        try:
            return json.loads(text[:last_bracket + 1])
        except json.JSONDecodeError:
            pass

    raise json.JSONDecodeError("Could not extract valid JSON array", text, 0)


def parse_response(text, batch):
    """Parse LLM JSON response. Override name with batch codes by position."""
    results = _extract_json_array(text)

    if len(results) != len(batch):
        print(f"  Warning: expected {len(batch)} results, got {len(results)}")

    # Override name by position to ensure we use the correct protocol code
    for i, r in enumerate(results):
        if i < len(batch):
            r["name"] = batch[i]["name"]

    return results


def parse_sub_response(text, batch):
    """Parse LLM sub-classification response. Override name with batch codes."""
    results = _extract_json_array(text)

    if len(results) != len(batch):
        print(f"  Warning: expected {len(batch)} results, got {len(results)}")

    for i, r in enumerate(results):
        if i < len(batch):
            r["name"] = batch[i]["name"]

    return results


def load_checkpoint(path):
    """Load checkpoint if exists."""
    if os.path.exists(path):
        with open(path, "r") as f:
            return json.load(f)
    return {"completed_batches": 0, "results": []}


def save_checkpoint(checkpoint, path):
    """Save checkpoint to disk."""
    with open(path, "w") as f:
        json.dump(checkpoint, f)


def read_protocol_codes():
    """Read protocol codes from success.txt, stripping .json suffix."""
    with open(SUCCESS_LIST, "r") as f:
        codes = []
        for line in f:
            name = line.strip()
            if not name:
                continue
            if name.endswith(".json"):
                name = name[:-5]
            codes.append(name)
    return codes


def classify_main():
    """Round 1: Three-way classification (common/specialized/non_bio)."""
    if not API_KEY:
        print("Error: API Key not set. Please fill in API_KEY in the script.")
        sys.exit(1)

    names = read_protocol_codes()
    print(f"Loaded {len(names)} protocols from success.txt")

    protocols = []
    no_readme = []
    for name in names:
        info = parse_readme(name)
        if info:
            protocols.append({"name": name, "info": info})
        else:
            no_readme.append(name)

    if no_readme:
        print(f"Warning: {len(no_readme)} protocols have no README.md, skipping them")

    print(f"Will classify {len(protocols)} protocols in batches of {BATCH_SIZE}")

    checkpoint = load_checkpoint(CHECKPOINT_FILE)
    all_results = checkpoint["results"]
    start_batch = checkpoint["completed_batches"]

    batches = []
    for i in range(0, len(protocols), BATCH_SIZE):
        batches.append(protocols[i: i + BATCH_SIZE])

    if start_batch > 0:
        print(f"Resuming from batch {start_batch + 1}/{len(batches)} ({len(all_results)} already classified)")

    for batch_idx in range(start_batch, len(batches)):
        batch = batches[batch_idx]
        print(f"Batch {batch_idx + 1}/{len(batches)} ({len(batch)} protocols)...", end=" ", flush=True)

        prompt = build_prompt(batch)
        response_text = call_llm(prompt)

        try:
            results = parse_response(response_text, batch)
            all_results.extend(results)
            print("OK")
        except (json.JSONDecodeError, KeyError) as e:
            print(f"Parse error: {e}")
            print(f"  Raw response: {response_text[:200]}")
            for item in batch:
                all_results.append({
                    "name": item["name"],
                    "classification": "unknown",
                    "reason": f"API response parse error: {e}",
                })

        checkpoint["completed_batches"] = batch_idx + 1
        checkpoint["results"] = all_results
        save_checkpoint(checkpoint, CHECKPOINT_FILE)

        if batch_idx < len(batches) - 1:
            time.sleep(1)

    # Build summary
    summary = {"common": 0, "specialized": 0, "non_bio": 0, "unknown": 0}
    for r in all_results:
        cls = r.get("classification", "unknown")
        summary[cls] = summary.get(cls, 0) + 1

    # Write common_protocols.txt
    common_names = [r["name"] for r in all_results if r.get("classification") == "common"]
    with open(OUTPUT_LIST, "w") as f:
        for name in common_names:
            f.write(name + "\n")

    # Write full results JSON
    output = {
        "total": len(all_results),
        "summary": summary,
        "no_readme": no_readme,
        "protocols": all_results,
    }
    with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    # Clean up checkpoint
    if os.path.exists(CHECKPOINT_FILE):
        os.remove(CHECKPOINT_FILE)

    print(f"\nDone! Summary: {summary}")
    print(f"  Common protocols: {OUTPUT_LIST} ({len(common_names)} protocols)")
    print(f"  Full results: {OUTPUT_JSON}")


def sub_classify_main():
    """Round 2: Sub-classify common protocols into experiment types + core flag."""
    if not API_KEY:
        print("Error: API Key not set. Please fill in API_KEY in the script.")
        sys.exit(1)

    # Load existing classification results
    if not os.path.exists(OUTPUT_JSON):
        print(f"Error: {OUTPUT_JSON} not found. Run round 1 first.")
        sys.exit(1)

    with open(OUTPUT_JSON, "r", encoding="utf-8") as f:
        data = json.load(f)

    # Build lookup: name -> index in protocols list
    proto_lookup = {}
    for i, p in enumerate(data["protocols"]):
        proto_lookup[p["name"]] = i

    # Filter common protocols that lack sub_category
    common_protos = [
        p for p in data["protocols"]
        if p.get("classification") == "common" and not p.get("sub_category")
    ]
    total_common = sum(1 for p in data["protocols"] if p.get("classification") == "common")
    print(f"Found {len(common_protos)} common protocols without sub_category (total common: {total_common})")

    if not common_protos:
        print("All common protocols already have sub_category. Nothing to do.")
        return

    # Enrich with README info for the prompt
    enriched = []
    for p in common_protos:
        info = parse_readme(p["name"])
        item = {"name": p["name"], "reason": p.get("reason", "")}
        if info:
            item["info"] = info
        enriched.append(item)

    # Load sub-classification checkpoint
    checkpoint = load_checkpoint(SUB_CHECKPOINT_FILE)
    all_sub_results = checkpoint["results"]
    start_batch = checkpoint["completed_batches"]

    batches = []
    for i in range(0, len(enriched), BATCH_SIZE):
        batches.append(enriched[i: i + BATCH_SIZE])

    if start_batch > 0:
        print(f"Resuming from batch {start_batch + 1}/{len(batches)} ({len(all_sub_results)} already sub-classified)")

    for batch_idx in range(start_batch, len(batches)):
        batch = batches[batch_idx]
        print(f"Sub-classify batch {batch_idx + 1}/{len(batches)} ({len(batch)} protocols)...", end=" ", flush=True)

        prompt = build_sub_prompt(batch)
        response_text = call_llm(prompt)

        try:
            results = parse_sub_response(response_text, batch)
            all_sub_results.extend(results)
            print("OK")
        except (json.JSONDecodeError, KeyError) as e:
            print(f"Parse error: {e}")
            print(f"  Raw response: {response_text[:200]}")
            for item in batch:
                all_sub_results.append({
                    "name": item["name"],
                    "sub_category": "other_common",
                    "is_core": False,
                    "sub_reason": f"API解析错误: {e}",
                })

        checkpoint["completed_batches"] = batch_idx + 1
        checkpoint["results"] = all_sub_results
        save_checkpoint(checkpoint, SUB_CHECKPOINT_FILE)

        if batch_idx < len(batches) - 1:
            time.sleep(1)

    # Merge sub-classification results back into main data
    sub_lookup = {}
    for r in all_sub_results:
        sub_lookup[r["name"]] = r

    for p in data["protocols"]:
        if p["name"] in sub_lookup:
            sub = sub_lookup[p["name"]]
            p["sub_category"] = sub.get("sub_category", "other_common")
            p["is_core"] = sub.get("is_core", False)
            p["sub_reason"] = sub.get("sub_reason", "")

    # Build sub_summary and core_count
    sub_summary = {}
    core_count = 0
    for p in data["protocols"]:
        if p.get("classification") == "common":
            sc = p.get("sub_category", "other_common")
            sub_summary[sc] = sub_summary.get(sc, 0) + 1
            if p.get("is_core"):
                core_count += 1

    data["sub_summary"] = sub_summary
    data["core_count"] = core_count

    # Write updated results
    with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    # Clean up checkpoint
    if os.path.exists(SUB_CHECKPOINT_FILE):
        os.remove(SUB_CHECKPOINT_FILE)

    print(f"\nDone! Sub-classification summary: {sub_summary}")
    print(f"  Core protocols: {core_count}")
    print(f"  Updated: {OUTPUT_JSON}")


def retry_unknown_main():
    """Re-classify protocols that were marked as 'unknown' due to parse errors."""
    if not API_KEY:
        print("Error: API Key not set.")
        sys.exit(1)

    if not os.path.exists(OUTPUT_JSON):
        print(f"Error: {OUTPUT_JSON} not found.")
        sys.exit(1)

    with open(OUTPUT_JSON, "r", encoding="utf-8") as f:
        data = json.load(f)

    unknown_protos = [p for p in data["protocols"] if p.get("classification") == "unknown"]
    print(f"Found {len(unknown_protos)} unknown protocols to retry")

    if not unknown_protos:
        print("Nothing to retry.")
        return

    # Build enriched batch with README info
    enriched = []
    for p in unknown_protos:
        info = parse_readme(p["name"])
        if info:
            enriched.append({"name": p["name"], "info": info})
        else:
            enriched.append({"name": p["name"], "info": {"title": "", "categories": "", "description": ""}})

    # Build name -> index in data["protocols"]
    name_to_idx = {}
    for i, p in enumerate(data["protocols"]):
        name_to_idx[p["name"]] = i

    batches = [enriched[i:i + BATCH_SIZE] for i in range(0, len(enriched), BATCH_SIZE)]

    for batch_idx, batch in enumerate(batches):
        print(f"Retry batch {batch_idx + 1}/{len(batches)} ({len(batch)} protocols)...", end=" ", flush=True)

        prompt = build_prompt(batch)
        response_text = call_llm(prompt)

        try:
            results = parse_response(response_text, batch)
            for r in results:
                idx = name_to_idx.get(r["name"])
                if idx is not None:
                    data["protocols"][idx] = r
            print("OK")
        except (json.JSONDecodeError, KeyError) as e:
            print(f"Parse error: {e}")
            print(f"  Raw response: {response_text[:200]}")

        if batch_idx < len(batches) - 1:
            time.sleep(1)

    # Rebuild summary
    summary = {"common": 0, "specialized": 0, "non_bio": 0, "unknown": 0}
    for r in data["protocols"]:
        cls = r.get("classification", "unknown")
        summary[cls] = summary.get(cls, 0) + 1

    data["summary"] = summary
    data["total"] = len(data["protocols"])

    # Update common_protocols.txt
    common_names = [r["name"] for r in data["protocols"] if r.get("classification") == "common"]
    with open(OUTPUT_LIST, "w") as f:
        for name in common_names:
            f.write(name + "\n")

    with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    print(f"\nDone! Updated summary: {summary}")


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""

    if cmd == "sub-classify":
        sub_classify_main()
    elif cmd == "retry-unknown":
        retry_unknown_main()
    elif cmd == "all":
        classify_main()
        sub_classify_main()
    else:
        classify_main()
