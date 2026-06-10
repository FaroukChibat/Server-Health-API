import requests
import time
from datetime import datetime

from fastapi import FastAPI, Query

app = FastAPI(title="ServerHealthAPI")

# ─── Configuration ───────────────────────────────────────

MODE_LIST = ["liveness", "readiness"]

TIMEOUT = 10

USERNAME = None
PASSWORD = None


# ─── Vérification d'un endpoint ──────────────────────────

def check_server(url: str, timeout: int = 10) -> dict:

    auth = (USERNAME, PASSWORD) if USERNAME and PASSWORD else None

    start = time.time()

    try:

        response = requests.get(
            url,
            timeout=timeout,
            allow_redirects=True,
            auth=auth,
        )

        elapsed = round((time.time() - start) * 1000)

        up = False

        # HTTP 200 obligatoire
        if response.status_code == 200:

            try:
                body = response.json()

                # Spring Boot Actuator
                up = body.get("status") == "UP"

            except Exception:
                # Si pas de JSON, on considère HTTP 200 comme OK
                up = True

        return {
            "url": url,
            "Status": up,
            "status_code": response.status_code,
            "response_time_ms": elapsed,
            "checked_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }

    except requests.exceptions.ConnectionError as e:

        elapsed = round((time.time() - start) * 1000)

        return {
            "url": url,
            "Status": False,
            "status_code": None,
            "response_time_ms": elapsed,
            "checked_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "error": f"Connexion refusée : {e}",
        }

    except requests.exceptions.Timeout:

        elapsed = round((time.time() - start) * 1000)

        return {
            "url": url,
            "Status": False,
            "status_code": None,
            "response_time_ms": elapsed,
            "checked_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "error": f"Timeout après {timeout}s",
        }

    except requests.exceptions.RequestException as e:

        elapsed = round((time.time() - start) * 1000)

        return {
            "url": url,
            "Status": False,
            "status_code": None,
            "response_time_ms": elapsed,
            "checked_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "error": str(e),
        }


# ─── Résumé serveur ──────────────────────────────────────

def build_server_summary(server: str, results: dict) -> dict:

    liveness = results.get("liveness", {})
    readiness = results.get("readiness", {})

    liveness_up = liveness.get("up", False)
    readiness_up = readiness.get("up", False)

    server_up = liveness_up and readiness_up

    return {
        "Serveur": server.replace("https://", "").replace("http://", ""),
        "Statut": "UP" if server_up else "DOWN",
        "Liveness": liveness,
        "Readiness": readiness,
        "Heure": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }


# ─── Vérification complète ───────────────────────────────

def run_checks(server_list: list[str]) -> list:

    data = []

    for server in server_list:

        mode_results = {}

        for mode in MODE_LIST:

            url = f"{server}/actuator/health/{mode}"

            result = check_server(url, TIMEOUT)

            mode_results[mode] = {
                "Status": result["Status"],
                "status_code": result["status_code"],
                "response_time_ms": result["response_time_ms"],
            }

        data.append(
            build_server_summary(
                server,
                mode_results
            )
        )

    return data


# ─── API ─────────────────────────────────────────────────

@app.get("/")
def root():
    return {
        "message": "Server Health API OK"
    }


@app.get("/ServerHealthAPI")
def get_server_health(
    servers: list[str] = Query(
        ...,
        description="Liste des serveurs à vérifier"
    )
):
    return run_checks(servers)