
import os
import sys
import requests
import jwt
import datetime

REST_BASE = os.getenv("REST_BASE_URL", "http://localhost:8080")
JWT_SECRET = "test-secret-key"

def generate_token(role="admin"):
    """Generate a test JWT token"""
    payload = {
        "sub": "testuser",
        "role": role,
        "exp": datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=1)
    }
    return jwt.encode(payload, JWT_SECRET, algorithm="HS256")

def test_no_auth():
    """Test API without authentication (default behavior)"""
    print("\n1. Testing without authentication (should work)...")
    resp = requests.get(f"{REST_BASE}/products")
    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
    print("✓ GET /products works without auth")

def test_with_auth():
    """Test API with JWT token"""
    print("\n2. Testing with JWT token...")
    token = generate_token("admin")
    headers = {"Authorization": f"Bearer {token}"}
    
    resp = requests.get(f"{REST_BASE}/products", headers=headers)
    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
    print("✓ GET /products works with admin token")
    
    resp = requests.patch(f"{REST_BASE}/products/1", params={"stock": 15}, headers=headers)
    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
    print("✓ PATCH /products/1 works with admin token")

def test_viewer_role():
    """Test viewer role (read-only)"""
    print("\n3. Testing viewer role...")
    token = generate_token("viewer")
    headers = {"Authorization": f"Bearer {token}"}
    
    resp = requests.get(f"{REST_BASE}/products", headers=headers)
    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
    print("✓ GET /products works with viewer token")
    
    resp = requests.patch(f"{REST_BASE}/products/1", params={"stock": 15}, headers=headers)
    assert resp.status_code == 403, f"Expected 403, got {resp.status_code}"
    print("✓ PATCH /products/1 blocked for viewer (403)")

def test_metrics():
    """Test metrics endpoint"""
    print("\n4. Testing metrics endpoint...")
    resp = requests.get(f"{REST_BASE}/metrics")
    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
    assert "api_rest_requests_total" in resp.text, "Metrics not found"
    print("✓ Metrics endpoint accessible")

def test_health():
    """Test health endpoint"""
    print("\n5. Testing health endpoint...")
    resp = requests.get(f"{REST_BASE}/health")
    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
    data = resp.json()
    assert data.get("status") == "healthy", "Health check failed"
    print("✓ Health check passed")

def main():
    print("=" * 60)
    print("Security Features Test Suite")
    print("=" * 60)
    print(f"REST API: {REST_BASE}")
    print(f"Note: Set JWT_SECRET={JWT_SECRET} in env to test auth")
    
    try:
        test_no_auth()
        test_metrics()
        test_health()
        
        
        print("\n" + "=" * 60)
        print("✓ All tests passed!")
        print("=" * 60)
    except AssertionError as e:
        print(f"\n✗ Test failed: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"\n✗ Error: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
