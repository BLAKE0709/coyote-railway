import httpx
import os

SWARM_API_URL = os.getenv("SWARM_API_URL", "http://localhost:8000")

def get_status() -> dict:
    """Get status of all swarms"""
    try:
        response = httpx.get(f"{SWARM_API_URL}/health", timeout=5)
        if response.status_code == 200:
            return response.json()
        return {"status": "unknown", "error": f"HTTP {response.status_code}"}
    except httpx.ConnectError:
        return {
            "status": "offline",
            "message": "Swarm API not reachable",
            "swarms": {
                "prophet": "unknown",
                "hydra": "unknown",
                "vulture": "unknown",
                "signal": "unknown"
            }
        }
    except Exception as e:
        return {"error": str(e)}

def get_prophet_stats() -> dict:
    """Get Prophet lead statistics"""
    try:
        response = httpx.get(f"{SWARM_API_URL}/swarms/prophet/stats", timeout=5)
        if response.status_code == 200:
            return response.json()
        return {"error": f"HTTP {response.status_code}"}
    except:
        return {
            "leads_today": 0,
            "leads_week": 0,
            "high_quality": 0,
            "status": "unknown"
        }

def start_swarm(name: str) -> dict:
    """Start a specific swarm"""
    try:
        response = httpx.post(f"{SWARM_API_URL}/swarms/{name}/start", timeout=5)
        return {"started": response.status_code == 200, "swarm": name}
    except Exception as e:
        return {"error": str(e)}

def stop_swarm(name: str) -> dict:
    """Stop a specific swarm"""
    try:
        response = httpx.post(f"{SWARM_API_URL}/swarms/{name}/stop", timeout=5)
        return {"stopped": response.status_code == 200, "swarm": name}
    except Exception as e:
        return {"error": str(e)}
