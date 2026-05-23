import requests
import json
import time

BASE_URL = "http://127.0.0.1:8000/api/v1"

def run_tests():
    print("--- 1. REGISTER ---")
    try:
        res = requests.post(f"{BASE_URL}/auth/register", json={"email": "test@demo.com", "password": "Test1234!", "full_name": "Test User"})
        print(res.status_code, res.text)
    except Exception as e:
        print("Registration failed:", e)

    print("\n--- 2. LOGIN ---")
    token = None
    try:
        res = requests.post(f"{BASE_URL}/auth/login", json={"email": "test@demo.com", "password": "Test1234!"})
        print(res.status_code)
        if res.status_code == 200:
            token = res.json().get("access_token")
            print("Token grabbed!")
        else:
            print("Login response:", res.text)
    except Exception as e:
        print("Login failed:", e)

    if not token:
        print("Skipping rest of tests due to missing token.")
        return

    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

    print("\n--- 3. CREATE PROFILE ---")
    profile_data = {
        "age": 28,
        "occupation": "Software Engineer",
        "country": "India",
        "monthly_income": 150000,
        "monthly_expenses": 60000,
        "risk_appetite": "aggressive",
        "investment_horizon": "long_term",
        "financial_goals": ["retirement", "FIRE"],
        "monthly_investment_amount": 30000
    }
    try:
        res = requests.post(f"{BASE_URL}/profile", headers=headers, json=profile_data)
        print(res.status_code, res.text)
    except Exception as e:
        print("Profile creation failed:", e)

    print("\n--- 4. GENERATE PORTFOLIO ---")
    try:
        portfolio_req = {
            "risk_score": 85.0,
            "investment_horizon": "long_term",
            "strategy": "max_sharpe",
            "initial_investment": 1000000,
            "ethical_investing": False
        }
        res = requests.post(f"{BASE_URL}/portfolio/generate", headers=headers, json=portfolio_req)
        print(res.status_code)
        print(json.dumps(res.json(), indent=2)[:500] + "...\n(truncated)")
    except Exception as e:
        print("Portfolio generation failed:", e)

if __name__ == "__main__":
    run_tests()
