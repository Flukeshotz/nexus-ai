from locust import HttpUser, task, between
import json

class NexusAILoadTester(HttpUser):
    wait_time = between(1, 3)

    def on_start(self):
        """Setup actions before running tasks (e.g., login)"""
        # For testing, we assume token is not required or hardcoded
        self.headers = {"Content-Type": "application/json"}

    @task(3)
    def test_health_check(self):
        self.client.get("/api/v1/health")

    @task(2)
    def test_portfolio_generation(self):
        payload = {
            "risk_category": "moderate",
            "investment_horizon": "medium_term",
            "amount": 100000,
            "esg_preference": "neutral",
            "strategy": "max_sharpe"
        }
        self.client.post(
            "/api/v1/portfolio/generate", 
            data=json.dumps(payload),
            headers=self.headers
        )

    @task(1)
    def test_chat_agent(self):
        payload = {
            "message": "What is the expected drawdown of this portfolio?",
            "portfolio_data": {
                "weights": {"SPY": 0.6, "TLT": 0.4},
                "metrics": {"max_drawdown_pct": 12.5}
            },
            "user_profile": {"age": 30, "risk_category": "moderate"}
        }
        self.client.post(
            "/api/v1/chat/message",
            data=json.dumps(payload),
            headers=self.headers
        )
        
    # To run this script:
    # locust -f locustfile.py --host=http://localhost:8000
