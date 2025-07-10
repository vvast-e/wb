from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime

from database import get_db
from crud.shop import (
    create_shop, get_shops_by_user, get_shop_by_id, 
    add_price_history, get_price_history_by_vendor, get_latest_price,
    update_shop, delete_shop
)
from crud.user import get_current_user
from models.user import User
from schemas import ShopCreate, ShopResponse, PriceHistoryCreate, PriceHistoryResponse

router = APIRouter(prefix="/shops", tags=["shops"])


@router.post("/", response_model=ShopResponse)
def create_shop_endpoint(
    shop: ShopCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Создать новый магазин"""
    try:
        db_shop = create_shop(
            db=db,
            name=shop.name,
            wb_name=shop.wb_name,
            user_id=current_user.id
        )
        return db_shop
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Ошибка при создании магазина: {str(e)}"
        )


@router.get("/", response_model=List[ShopResponse])
def get_user_shops(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Получить магазины пользователя"""
    shops = get_shops_by_user(db, current_user.id)
    return shops


@router.get("/{shop_id}", response_model=ShopResponse)
def get_shop(
    shop_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Получить магазин по ID"""
    shop = get_shop_by_id(db, shop_id)
    if not shop:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Магазин не найден"
        )
    
    # Проверяем, что магазин принадлежит пользователю
    if shop.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Нет доступа к этому магазину"
        )
    
    return shop


@router.put("/{shop_id}", response_model=ShopResponse)
def update_shop_endpoint(
    shop_id: int,
    shop_update: ShopCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Обновить магазин"""
    shop = get_shop_by_id(db, shop_id)
    if not shop:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Магазин не найден"
        )
    
    if shop.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Нет доступа к этому магазину"
        )
    
    updated_shop = update_shop(
        db=db,
        shop_id=shop_id,
        name=shop_update.name,
        wb_name=shop_update.wb_name
    )
    
    return updated_shop


@router.delete("/{shop_id}")
def delete_shop_endpoint(
    shop_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Удалить магазин"""
    shop = get_shop_by_id(db, shop_id)
    if not shop:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Магазин не найден"
        )
    
    if shop.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Нет доступа к этому магазину"
        )
    
    success = delete_shop(db, shop_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ошибка при удалении магазина"
        )
    
    return {"message": "Магазин успешно удален"}


@router.post("/{shop_id}/prices", response_model=PriceHistoryResponse)
def add_price_history_endpoint(
    shop_id: int,
    price_data: PriceHistoryCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Добавить запись в историю цен"""
    shop = get_shop_by_id(db, shop_id)
    if not shop:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Магазин не найден"
        )
    
    if shop.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Нет доступа к этому магазину"
        )
    
    # Получаем последнюю цену для сравнения
    latest_price = get_latest_price(db, price_data.vendor_code, shop_id)
    old_price = latest_price.new_price if latest_price else None
    
    price_history = add_price_history(
        db=db,
        vendor_code=price_data.vendor_code,
        shop_id=shop_id,
        nm_id=price_data.nm_id,
        new_price=price_data.new_price,
        old_price=old_price
    )
    
    return price_history


@router.get("/{shop_id}/prices/{vendor_code}", response_model=List[PriceHistoryResponse])
def get_price_history(
    shop_id: int,
    vendor_code: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Получить историю цен товара"""
    shop = get_shop_by_id(db, shop_id)
    if not shop:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Магазин не найден"
        )
    
    if shop.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Нет доступа к этому магазину"
        )
    
    price_history = get_price_history_by_vendor(db, vendor_code, shop_id)
    return price_history 