"""
API routes for print gateway.

Base URL: /v1
"""

from datetime import datetime
from fastapi import APIRouter, File, UploadFile, HTTPException, Query
from fastapi.responses import JSONResponse
from typing import Optional

from src.api.dependencies import get_printer_registry, get_queue_manager, get_router
from src.printers.base import PrintJob, PrinterStatus
from src.validation import validate_label_image, validate_pdf

router = APIRouter(prefix="/v1")

# Track server start time
_server_start_time = datetime.now()


@router.get("/health")
async def health_check(detailed: bool = Query(default=False)):
    """
    Health check endpoint.

    Args:
        detailed: If true, include printer status and diagnostics
    """
    if not detailed:
        return {"status": "ok"}

    # Detailed health check
    registry = get_printer_registry()
    queue_manager = get_queue_manager()
    print_router = get_router()

    statuses = await registry.get_all_status()

    printers_ok = all(
        status in (PrinterStatus.READY, PrinterStatus.BUSY)
        for status in statuses.values()
    )

    total_queued = sum(
        q.get_status()["queued"]
        for q in queue_manager.get_all_queues().values()
    )

    uptime_seconds = (datetime.now() - _server_start_time).total_seconds()

    return {
        "status": "ok" if printers_ok else "degraded",
        "uptime_seconds": int(uptime_seconds),
        "printers": {
            pid: {
                "status": status.value,
                "online": status in (PrinterStatus.READY, PrinterStatus.BUSY)
            }
            for pid, status in statuses.items()
        },
        "queue": {
            "total_jobs_queued": total_queued
        },
        "intents_configured": len(print_router.list_intents())
    }


@router.get("/status")
async def get_status():
    """Get status of all printers."""
    registry = get_printer_registry()
    statuses = await registry.get_all_status()

    return {
        "printers": {
            printer_id: {
                "name": registry.get(printer_id).name,
                "status": status.value,
                "online": status in (PrinterStatus.READY, PrinterStatus.BUSY)
            }
            for printer_id, status in statuses.items()
        }
    }


@router.get("/queue")
async def get_queue(printer_id: Optional[str] = None):
    """Get queue status for all or specific printer."""
    queue_manager = get_queue_manager()

    if printer_id:
        queue = queue_manager.get_queue(printer_id)
        if not queue:
            raise HTTPException(status_code=404, detail=f"Printer not found: {printer_id}")
        return {
            "printer_id": printer_id,
            "queue": queue.get_queue(),
            "status": queue.get_status()
        }

    # Return all queues
    return {
        "queues": {
            pid: {
                "queue": q.get_queue(),
                "status": q.get_status()
            }
            for pid, q in queue_manager.get_all_queues().items()
        }
    }


@router.post("/print/label")
async def print_label(
    file: UploadFile = File(...),
    printer_id: str = Query(default="label", description="Target label printer ID"),
    copies: int = Query(default=1, ge=1, le=10)
):
    """
    Print a label image.

    Accepts PNG images that must be:
    - Exactly 720px wide
    - Monochrome (black and white only)

    Returns job ID for tracking.
    """
    registry = get_printer_registry()
    queue_manager = get_queue_manager()

    # Check printer exists
    printer = registry.get(printer_id)
    if not printer:
        raise HTTPException(status_code=404, detail=f"Printer not found: {printer_id}")

    # Check printer is online
    status = await printer.get_status()
    if status == PrinterStatus.OFFLINE:
        raise HTTPException(status_code=503, detail="Printer offline")
    if status == PrinterStatus.ERROR:
        raise HTTPException(status_code=503, detail="Printer error")

    # Read and validate image
    data = await file.read()

    if not data:
        raise HTTPException(status_code=400, detail="Empty file")

    # Validate content type
    content_type = file.content_type or "application/octet-stream"
    if content_type not in ("image/png", "application/octet-stream"):
        raise HTTPException(
            status_code=400,
            detail=f"Invalid content type: {content_type}. Expected: image/png"
        )

    # Validate image requirements
    validation = validate_label_image(data)
    if not validation.valid:
        return JSONResponse(
            status_code=400,
            content={
                "error": validation.error,
                "code": validation.error_code,
                "details": {
                    "width": validation.width,
                    "height": validation.height,
                    "mode": validation.mode
                }
            }
        )

    # Create print job
    job = PrintJob(
        printer_id=printer_id,
        filename=file.filename or "label.png",
        data=data,
        content_type="image/png",
        copies=copies
    )

    # Validate job with printer
    is_valid, error = printer.validate_job(job)
    if not is_valid:
        raise HTTPException(status_code=400, detail=error)

    # Queue the job
    queue = queue_manager.get_or_create_queue(printer_id, printer.print)
    try:
        queued = await queue.add(job)
    except Exception as e:
        raise HTTPException(status_code=503, detail=str(e))

    return {
        "job_id": job.id,
        "status": queued.status.value,
        "message": "Job queued for printing",
        "queue_position": len(queue.get_queue())
    }


@router.post("/print/document")
async def print_document(
    file: UploadFile = File(...),
    printer_id: str = Query(default="document", description="Target document printer ID"),
    copies: int = Query(default=1, ge=1, le=100)
):
    """
    Print a PDF document.

    Accepts PDF files only.
    Returns job ID for tracking.
    """
    registry = get_printer_registry()
    queue_manager = get_queue_manager()

    # Check printer exists
    printer = registry.get(printer_id)
    if not printer:
        raise HTTPException(status_code=404, detail=f"Printer not found: {printer_id}")

    # Check printer is online
    status = await printer.get_status()
    if status == PrinterStatus.OFFLINE:
        raise HTTPException(status_code=503, detail="Printer offline")
    if status == PrinterStatus.ERROR:
        raise HTTPException(status_code=503, detail="Printer error")

    # Read file
    data = await file.read()

    if not data:
        raise HTTPException(status_code=400, detail="Empty file")

    # Validate PDF
    validation = validate_pdf(data)
    if not validation.valid:
        return JSONResponse(
            status_code=400,
            content={
                "error": validation.error,
                "code": validation.error_code
            }
        )

    # Create print job
    job = PrintJob(
        printer_id=printer_id,
        filename=file.filename or "document.pdf",
        data=data,
        content_type="application/pdf",
        copies=copies
    )

    # Validate job with printer
    is_valid, error = printer.validate_job(job)
    if not is_valid:
        raise HTTPException(status_code=400, detail=error)

    # Queue the job
    queue = queue_manager.get_or_create_queue(printer_id, printer.print)
    try:
        queued = await queue.add(job)
    except Exception as e:
        raise HTTPException(status_code=503, detail=str(e))

    return {
        "job_id": job.id,
        "status": queued.status.value,
        "message": "Job queued for printing",
        "queue_position": len(queue.get_queue()),
        "page_count": validation.page_count
    }


@router.get("/job/{job_id}")
async def get_job(job_id: str):
    """Get status of a specific print job."""
    queue_manager = get_queue_manager()

    for queue in queue_manager.get_all_queues().values():
        job = queue.get_job(job_id)
        if job:
            return {
                "id": job.job.id,
                "printer_id": job.job.printer_id,
                "filename": job.job.filename,
                "status": job.status.value,
                "queued_at": job.queued_at.isoformat(),
                "started_at": job.started_at.isoformat() if job.started_at else None,
                "completed_at": job.completed_at.isoformat() if job.completed_at else None,
                "error": job.error
            }

    raise HTTPException(status_code=404, detail=f"Job not found: {job_id}")


@router.delete("/job/{job_id}")
async def cancel_job(job_id: str):
    """Cancel a queued print job."""
    queue_manager = get_queue_manager()

    for queue in queue_manager.get_all_queues().values():
        if await queue.cancel(job_id):
            return {"message": "Job cancelled", "job_id": job_id}

    raise HTTPException(status_code=404, detail=f"Job not found or already processing: {job_id}")


# =============================================================================
# Intent-based routing (unified print endpoint)
# =============================================================================

@router.get("/intents")
async def list_intents():
    """
    List all configured print intents.

    Use this to discover what intents are available for the /print endpoint.
    """
    print_router = get_router()
    return {
        "intents": print_router.list_intents()
    }


@router.post("/print")
async def print_with_intent(
    file: UploadFile = File(...),
    intent: str = Query(..., description="Print intent (e.g., 'shipping-label', 'invoice')"),
    copies: int = Query(default=1, ge=1, le=100)
):
    """
    Unified print endpoint with intent-based routing.

    Send a file with an intent (what you want to print), and the server
    routes it to the correct printer based on configuration.

    Examples:
        POST /v1/print?intent=shipping-label
        POST /v1/print?intent=invoice
        POST /v1/print?intent=price-tag

    The server config maps intents to physical printers, so your app
    doesn't need to know about printer IDs.
    """
    registry = get_printer_registry()
    queue_manager = get_queue_manager()
    print_router = get_router()

    # Read file first to determine content type
    data = await file.read()
    if not data:
        raise HTTPException(status_code=400, detail="Empty file")

    # Determine content type
    content_type = file.content_type or "application/octet-stream"
    is_image = content_type.startswith("image/") or content_type == "application/octet-stream"
    is_pdf = content_type == "application/pdf" or (file.filename and file.filename.lower().endswith(".pdf"))

    # Resolve intent to printer
    if is_image:
        detected_type = "image/png"
    elif is_pdf:
        detected_type = "application/pdf"
    else:
        detected_type = content_type

    printer_id = print_router.resolve(intent)
    if not printer_id:
        # Check if intent exists at all
        available = list(print_router.list_intents().keys())
        if available:
            raise HTTPException(
                status_code=400,
                detail=f"Unknown intent: '{intent}'. Available: {available}"
            )
        else:
            # No intents configured, fall back to defaults
            printer_id = print_router.resolve_or_default(intent, detected_type)

    # Get printer
    printer = registry.get(printer_id)
    if not printer:
        raise HTTPException(
            status_code=500,
            detail=f"Intent '{intent}' maps to printer '{printer_id}' which doesn't exist. Check server config."
        )

    # Check printer status
    status = await printer.get_status()
    if status == PrinterStatus.OFFLINE:
        raise HTTPException(status_code=503, detail=f"Printer '{printer_id}' is offline")
    if status == PrinterStatus.ERROR:
        raise HTTPException(status_code=503, detail=f"Printer '{printer_id}' has an error")

    # Validate based on content type
    if is_image or detected_type == "image/png":
        validation = validate_label_image(data)
        if not validation.valid:
            return JSONResponse(
                status_code=400,
                content={
                    "error": validation.error,
                    "code": validation.error_code,
                    "details": {
                        "width": validation.width,
                        "height": validation.height,
                        "mode": validation.mode
                    }
                }
            )
        final_content_type = "image/png"
    elif is_pdf or detected_type == "application/pdf":
        validation = validate_pdf(data)
        if not validation.valid:
            return JSONResponse(
                status_code=400,
                content={
                    "error": validation.error,
                    "code": validation.error_code
                }
            )
        final_content_type = "application/pdf"
    else:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported content type: {content_type}. Use PNG for labels or PDF for documents."
        )

    # Create job
    job = PrintJob(
        printer_id=printer_id,
        filename=file.filename or f"print.{final_content_type.split('/')[-1]}",
        data=data,
        content_type=final_content_type,
        copies=copies
    )

    # Validate with printer
    is_valid, error = printer.validate_job(job)
    if not is_valid:
        raise HTTPException(status_code=400, detail=error)

    # Queue it
    queue = queue_manager.get_or_create_queue(printer_id, printer.print)
    try:
        queued = await queue.add(job)
    except Exception as e:
        raise HTTPException(status_code=503, detail=str(e))

    return {
        "job_id": job.id,
        "intent": intent,
        "printer_id": printer_id,
        "status": queued.status.value,
        "message": "Job queued for printing",
        "queue_position": len(queue.get_queue())
    }
