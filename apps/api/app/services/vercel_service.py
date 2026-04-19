import httpx
import os
from typing import List, Dict, Optional

class VercelService:
    def __init__(self, team_slug: Optional[str] = "declan-butlers-projects"):
        self.team_slug = team_slug
        # teamId will be resolved if its a team_ prefixed string or the slug itself
        self.team_id = os.getenv("VERCEL_TEAM_ID") 
        self.token = os.getenv("VERCEL_TOKEN")
        self.api_base = "https://api.vercel.com"
        
        if not self.token:
             print("WARNING: VERCEL_TOKEN not found in environment.")

    @property
    def headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json"
        }

    def _get_params(self, params: Optional[Dict] = None) -> Dict:
        p = params or {}
        if self.team_id:
            p["teamId"] = self.team_id
        return p

    def list_projects(self) -> List[Dict]:
        url = f"{self.api_base}/v9/projects"
        with httpx.Client() as client:
            try:
                response = client.get(url, headers=self.headers, params=self._get_params())
                response.raise_for_status()
                data = response.json()
                
                projects = []
                for p in data.get("projects", []):
                    projects.append({
                        "name": p["name"],
                        "url": p.get("targets", {}).get("production", {}).get("url", "no-url"),
                        "updated": "recent"
                    })
                return projects
            except Exception as e:
                print(f"Error listing projects: {e}")
                return []

    def list_deployments(self) -> List[Dict]:
        url = f"{self.api_base}/v6/deployments"
        with httpx.Client() as client:
            try:
                response = client.get(url, headers=self.headers, params=self._get_params())
                response.raise_for_status()
                data = response.json()
                
                deployments = []
                for d in data.get("deployments", []):
                    deployments.append({
                        "id": d["uid"],
                        "project": d["name"],
                        "url": d["url"],
                        "status": d["state"],
                        "type": "Production" if d.get("target") == "production" else "Preview",
                        "age": "recent"
                    })
                return deployments
            except Exception as e:
                print(f"Error listing deployments: {e}")
                return []

    def remove_deployment(self, deployment_id: str) -> str:
        url = f"{self.api_base}/v13/deployments/{deployment_id}"
        with httpx.Client() as client:
            response = client.delete(url, headers=self.headers, params=self._get_params())
            response.raise_for_status()
            return f"Removed deployment {deployment_id}"

    def stop_active_deployments(self) -> List[str]:
        deployments = self.list_deployments()
        stopped = []
        for dep in deployments:
            if dep["status"] in ["BUILDING", "INITIALIZING"]:
                self.remove_deployment(dep["id"])
                stopped.append(f"{dep['project']} ({dep['url']})")
        return stopped

    def stop_all_production_deployments(self) -> List[str]:
        deployments = self.list_deployments()
        stopped = []
        for dep in deployments:
            if dep["type"] == "Production":
                try:
                    self.remove_deployment(dep["id"])
                    stopped.append(f"{dep['project']} ({dep['url']})")
                except Exception as e:
                    print(f"Failed to remove {dep['url']}: {e}")
        return stopped
