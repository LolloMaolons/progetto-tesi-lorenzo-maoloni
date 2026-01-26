import requests
import json
import os
import time
from datetime import datetime

REST_URL = "http://localhost:8080/products"
REST_SINGLE_URL = "http://localhost:8080/products/1"
GRAPHQL_URL = "http://localhost:4000/"
ITERATIONS = 1
HEADERS = {"Content-Type": "application/json"}
OUTPUT_FILE = "test-3-bandwidth-field-selection.json"

def check_services():
    try:
        r = requests.get("http://localhost:8080/health", timeout=3)
        if r.status_code != 200:
            print("[ERRORE] api-rest non disponibile")
            return False
        r2 = requests.post(GRAPHQL_URL, json={"query": "{ __typename }"}, timeout=3)
        if r2.status_code != 200:
            print("[ERRORE] gateway-graphql non disponibile")
            return False
        return True
    except Exception as e:
        print(f"[ERRORE] Servizi non disponibili: {e}")
        return False

def reset_catalog():
    try:
        r = requests.post("http://localhost:8080/reset", timeout=5)
        return r.status_code == 200
    except Exception:
        return False

def get_payload_info(response):
    payload = response.content
    headers = response.headers
    payload_bytes = len(payload)
    headers_bytes = sum(len(str(k)) + len(str(v)) for k, v in headers.items())
    return payload_bytes, headers_bytes, payload_bytes + headers_bytes

def graphql_query(query):
    r = requests.post(GRAPHQL_URL, headers=HEADERS, json={"query": query}, timeout=5)
    return r

def main():
    print("=" * 70)
    print("TEST 3: Bandwidth Efficiency - Field Selection", flush=True)
    print("=" * 70)
    if not check_services():
        print("Servizi non disponibili. Esci.")
        return
    reset_catalog()
    time.sleep(2)
    print("[REST] Lista prodotti...", flush=True)
    rest_resp = requests.get(REST_URL, timeout=5)
    rest_payload, rest_headers, rest_total = get_payload_info(rest_resp)
    print("[GraphQL] Tutti campi...", flush=True)
    query_all = """{ products { id name price stock category description } }"""
    gql_all_resp = graphql_query(query_all)
    gql_all_payload, gql_all_headers, gql_all_total = get_payload_info(gql_all_resp)
    print("[GraphQL] 3 campi...", flush=True)
    query_sel = """{ products { id name price } }"""
    gql_sel_resp = graphql_query(query_sel)
    gql_sel_payload, gql_sel_headers, gql_sel_total = get_payload_info(gql_sel_resp)
    print("[REST] Singolo prodotto...", flush=True)
    rest_single_resp = requests.get(REST_SINGLE_URL, timeout=5)
    rest_single_payload, rest_single_headers, rest_single_total = get_payload_info(rest_single_resp)
    print("[GraphQL] Singolo prodotto...", flush=True)
    query_single = """{ product(id: 1) { id name price stock category description } }"""
    gql_single_resp = graphql_query(query_single)
    gql_single_payload, gql_single_headers, gql_single_total = get_payload_info(gql_single_resp)
    reduction = round((rest_payload - gql_sel_payload) / rest_payload * 100, 1) if rest_payload else 0
    print("[GraphQL] Singolo prodotto (field selection)...", flush=True)
    query_single_sel = """{ product(id: 1) { id name price } }"""
    gql_single_sel_resp = graphql_query(query_single_sel)
    gql_single_sel_payload, gql_single_sel_headers, gql_single_sel_total = get_payload_info(gql_single_sel_resp)
    print("[REST] 5 prodotti + raccomandazioni (test 2)...", flush=True)
    rest_5_total_payload = 0
    rest_5_total_headers = 0
    for pid in range(1, 6):
        resp_prod = requests.get(f"{REST_URL}/{pid}", timeout=5)
        pld_prod, hdr_prod, _ = get_payload_info(resp_prod)
        resp_rec = requests.get(f"{REST_URL}/{pid}/recommendations", timeout=5)
        pld_rec, hdr_rec, _ = get_payload_info(resp_rec)
        rest_5_total_payload += pld_prod + pld_rec
        rest_5_total_headers += hdr_prod + hdr_rec
    rest_5_total = rest_5_total_payload + rest_5_total_headers

    print("[GraphQL] 5 prodotti + raccomandazioni (test 2, tutti campi)...", flush=True)
    products_query = "\n".join([
        f"p{pid}: product(id: {pid}) {{ id name price stock recommendations(limit: 3) {{ id name price }} }}" for pid in range(1, 6)
    ])
    query_5_all = f"""{{\n{products_query}\n}}"""
    gql_5_all_resp = graphql_query(query_5_all)
    gql_5_all_payload, gql_5_all_headers, gql_5_all_total = get_payload_info(gql_5_all_resp)

    print("[GraphQL] 5 prodotti + raccomandazioni (test 2, field selection)...", flush=True)
    products_query_sel = "\n".join([
        f"p{pid}: product(id: {pid}) {{ id name price recommendations(limit: 3) {{ id name price }} }}" for pid in range(1, 6)
    ])
    query_5_sel = f"""{{\n{products_query_sel}\n}}"""
    gql_5_sel_resp = graphql_query(query_5_sel)
    gql_5_sel_payload, gql_5_sel_headers, gql_5_sel_total = get_payload_info(gql_5_sel_resp)

    reduction_5 = round((rest_5_total_payload - gql_5_sel_payload) / rest_5_total_payload * 100, 1) if rest_5_total_payload else 0

    reduction_2 = round((rest_single_payload - gql_single_sel_payload) / rest_single_payload * 100, 1) if rest_single_payload else 0
    results = {
        "test": "Bandwidth Efficiency - Field Selection",
        "data": datetime.now().isoformat(),
        "configuration": {
            "rest_url": REST_URL,
            "graphql_url": GRAPHQL_URL
        },
        "results": {
            "scenario_1": {
                "rest": {"payload": rest_payload, "headers": rest_headers, "total": rest_total},
                "graphql_all": {"payload": gql_all_payload, "headers": gql_all_headers, "total": gql_all_total},
                "graphql_selective": {"payload": gql_sel_payload, "headers": gql_sel_headers, "total": gql_sel_total},
                "reduction_percent": reduction
            },
            "scenario_2": {
                "rest": {"payload": rest_single_payload, "headers": rest_single_headers, "total": rest_single_total},
                "graphql_all": {"payload": gql_single_payload, "headers": gql_single_headers, "total": gql_single_total},
                "graphql_selective": {"payload": gql_single_sel_payload, "headers": gql_single_sel_headers, "total": gql_single_sel_total},
                "reduction_percent": reduction_2
            },
            "scenario_3": {
                "rest_5": {"payload": rest_5_total_payload, "headers": rest_5_total_headers, "total": rest_5_total},
                "graphql_5_all": {"payload": gql_5_all_payload, "headers": gql_5_all_headers, "total": gql_5_all_total},
                "graphql_5_selective": {"payload": gql_5_sel_payload, "headers": gql_5_sel_headers, "total": gql_5_sel_total},
                "reduction_percent": reduction_5
            }
        }
    }
    output_dir = os.path.join(os.path.dirname(__file__), '..', 'risultati-misurazioni')
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, OUTPUT_FILE)
    with open(output_path, 'w') as f:
        json.dump(results, f, indent=2)
    print(f"\nRisultati salvati: {output_path}")

if __name__ == "__main__":
    main()
