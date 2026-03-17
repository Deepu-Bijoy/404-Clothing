"""
Quick route verification script - checks that all key routes return expected HTTP status codes.
Run with: python verify_routes.py
"""
import urllib.request
import urllib.error

BASE = "http://127.0.0.1:5000"

routes = [
    ("/", 200, "Homepage"),
    ("/search?q=shirt", 200, "Search (basic)"),
    ("/search?q=shirt&sort=price_low", 200, "Search (sort price low)"),
    ("/search?q=shirt&sort=price_high", 200, "Search (sort price high)"),
    ("/search?q=shirt&sort=rating", 200, "Search (sort rating)"),
    ("/search?q=shirt&max_price=500", 200, "Search (price filter)"),
    ("/auth/login", 200, "Login Page"),
    ("/auth/register", 200, "Register Page"),
    ("/cart/view", 200, "Cart (redirect to login or show cart)"),
    ("/wishlist", 302, "Wishlist (redirects to login)"),
    ("/my-orders", 302, "My Orders (redirects to login)"),
    ("/shop/size-guide", 200, "Size Guide"),
    ("/size-guide", 200, "Size Guide"),
]

print("\n=== Route Verification ===\n")
all_ok = True
for path, expected, label in routes:
    url = BASE + path
    try:
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=5) as resp:
            code = resp.status
    except urllib.error.HTTPError as e:
        code = e.code
    except urllib.error.URLError as e:
        code = f"CONN_ERR: {e.reason}"
    except Exception as e:
        code = f"ERR: {e}"

    ok = str(code) == str(expected)
    status = "OK  " if ok else "FAIL"
    if not ok:
        all_ok = False
    print(f"  {status} [{code}] {label}")

print()
if all_ok:
    print("All routes CHECK OK.")
else:
    print("Some routes failed - check above.")
