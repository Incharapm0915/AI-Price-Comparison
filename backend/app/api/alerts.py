"""POST/GET /api/alerts, DELETE /api/alerts/{id} — price-drop alerts."""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.schemas.alert import AlertOut, CreateAlertRequest
from app.services.alert_service import create_alert, delete_alert, list_alerts

router = APIRouter()


@router.post("", response_model=AlertOut, status_code=201)
def create(payload: CreateAlertRequest, db: Session = Depends(get_db)) -> AlertOut:
    alert = create_alert(db, payload)
    if alert is None:
        raise HTTPException(status_code=404, detail={"code": "LISTING_NOT_FOUND", "message": "No listing with that id"})
    db.commit()
    return alert


@router.get("", response_model=list[AlertOut])
def list_for_email(email: str = Query(...), db: Session = Depends(get_db)) -> list[AlertOut]:
    return list_alerts(db, email)


@router.delete("/{alert_id}", status_code=204)
def delete(alert_id: str, db: Session = Depends(get_db)) -> None:
    if not delete_alert(db, alert_id):
        raise HTTPException(status_code=404, detail={"code": "ALERT_NOT_FOUND", "message": "No alert with that id"})
    db.commit()
