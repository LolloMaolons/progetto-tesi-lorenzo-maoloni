import sys
import re
import statistics

WARMUP = 3

def parse_latencies(lines):
    latencies = []
    for line in lines:
        match = re.search(r'Latency \d+:\s+([\d.]+)\s*ms', line)
        if match:
            latencies.append(float(match.group(1)))
    return latencies

def calculate_stats(latencies):
    if not latencies:
        return None, None
    mean = statistics.mean(latencies)
    p95_idx = int(len(latencies) * 0.95)
    sorted_latencies = sorted(latencies)
    p95 = sorted_latencies[min(p95_idx, len(sorted_latencies) - 1)]
    return mean, p95

def main():
    lines = sys.stdin.readlines()
    latencies = parse_latencies(lines)
    if len(latencies) > WARMUP:
        original = len(latencies)
        latencies = latencies[WARMUP:]
        print(f"\n({WARMUP} misurazioni di warmup ignorate, statistiche calcolate su {len(latencies)}/{original} misurazioni)")
    else:
        print(f"\n((Avviso: meno di {WARMUP+1} misurazioni, nessuna scartata))")

    if not latencies:
        print("No latency data found in input", file=sys.stderr)
        sys.exit(1)
    mean, p95 = calculate_stats(latencies)
    print(f"\nWebSocket Latency Statistics")
    print(f"=============================")
    print(f"Total measurements (used): {len(latencies)}")
    print(f"Mean latency:       {mean:.2f} ms")
    print(f"P95 latency:        {p95:.2f} ms")
    print(f"Min latency:        {min(latencies):.2f} ms")
    print(f"Max latency:        {max(latencies):.2f} ms")
    if len(latencies) > 1:
        stdev = statistics.stdev(latencies)
        print(f"Std deviation:      {stdev:.2f} ms")

if __name__ == "__main__":
    main()