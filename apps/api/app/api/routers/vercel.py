from fastapi import APIRouter, HTTPException, Depends
from app.services.vercel_service import VercelService
from typing import List, Dict

router = APIRouter(prefix="/vercel", tags=["vercel"])

def get_vercel_service():
    return VercelService()

@router.get("/projects")
async def list_projects(service: VercelService = Depends(get_vercel_service)):
    try:
        return service.list_projects()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/deployments")
async def list_deployments(service: VercelService = Depends(get_vercel_service)):
    try:
        return service.list_deployments()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/projects/{project_name}/latest")
async def get_latest_deployment(
    project_name: str, 
    service: VercelService = Depends(get_vercel_service)
):
    try:
        return service.get_latest_deployment(project_name)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/stop")
async def stop_all(service: VercelService = Depends(get_vercel_service)):
    try:
        stopped = service.stop_active_deployments()
        if not stopped:
            return {"message": "No in-progress deployments found to stop."}
        return {"message": f"Stopped deployments for: {', '.join(stopped)}"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/stop-production")
async def stop_production(service: VercelService = Depends(get_vercel_service)):
    try:
        stopped = service.stop_all_production_deployments()
        if not stopped:
            return {"message": "No production deployments found to stop."}
        return {"message": f"Successfully removed production deployments for: {', '.join(stopped)}"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
