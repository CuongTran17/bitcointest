from fastapi import APIRouter, Query

from app.schemas import BlockDetailRead, BlockListRead
from app.services import blocks as block_service

router = APIRouter(prefix="/blocks", tags=["blocks"])


@router.get("", response_model=BlockListRead)
def list_blocks(limit: int = Query(default=20, ge=1, le=100)):
    return block_service.list_blocks(limit)


@router.get("/{block_ref}", response_model=BlockDetailRead)
def get_block_detail(block_ref: str):
    return block_service.get_block_detail(block_ref)
