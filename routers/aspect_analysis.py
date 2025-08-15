from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import List, Optional, Dict
import json
import asyncio
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from database import get_db
from models.feedback import Feedback
from sqlalchemy import select
import logging
from utils.aspect_analyzer import aspect_analyzer
from utils.ai_aspect_analyzer import ai_aspect_analyzer

router = APIRouter(prefix="/aspect-analysis", tags=["aspect-analysis"])

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AspectAnalysisRequest(BaseModel):
    product_name: str
    feedback_ids: Optional[List[int]] = None
    limit: Optional[int] = 50  # Увеличиваем с 30 до 50 для тестирования
    test_mode: Optional[bool] = False  # Режим тестирования на первых отзывах

class AspectAnalysisResponse(BaseModel):
    general_dictionary: List[str]
    no_duplicates_dictionary: List[str]
    no_synonyms_dictionary: List[str]
    processing_time: float

class AspectDictionaryRequest(BaseModel):
    aspects: List[str]
    synonym_journal: List[str]

class SingleReviewAspectRequest(BaseModel):
    review_text: str
    rating: int

class SingleReviewAspectResponse(BaseModel):
    positive_aspects: List[str]
    negative_aspects: List[str]
    processing_time: float



@router.post("/analyze", response_model=AspectAnalysisResponse)
async def analyze_aspects(
    request: AspectAnalysisRequest,
    db: AsyncSession = Depends(get_db)
):
    """Анализ аспектов товара на основе отзывов"""
    start_time = asyncio.get_event_loop().time()
    
    try:
        # Валидация лимитов для стабильной работы с ИИ
        if request.limit and request.limit > 50:
            logger.warning(f"Запрошено {request.limit} отзывов, что может превысить лимиты ИИ. Рекомендуется не более 30-50 отзывов.")
        
        # Получаем отзывы из базы данных
        if request.feedback_ids:
            query = select(Feedback).where(Feedback.id.in_(request.feedback_ids))
        elif request.test_mode:
            # Тестовый режим: берем первые отзывы из БД
            query = select(Feedback).order_by(Feedback.id.asc()).limit(request.limit)
            logger.info(f"Тестовый режим: анализируем первые {request.limit} отзывов из БД")
        else:
            query = select(Feedback).limit(request.limit)
        
        result = await db.execute(query)
        feedbacks = result.scalars().all()
        
        if not feedbacks:
            raise HTTPException(status_code=404, detail="Отзывы не найдены")
        
        logger.info(f"Анализируем {len(feedbacks)} отзывов для товара '{request.product_name}'")
        
        # Формируем список отзывов с оценками
        reviews_with_ratings = []
        for feedback in feedbacks:
            review_text = feedback.text or ""
            rating = feedback.rating or 0
            reviews_with_ratings.append(f"{review_text}; Оценка {rating}/5")
        
        # Генерируем словари используя ИИ-анализатор, если доступен, иначе локальный
        if ai_aspect_analyzer:
            try:
                analysis_result = await ai_aspect_analyzer.analyze_reviews(reviews_with_ratings, request.product_name)
                general_dict = analysis_result["general_dictionary"]
                no_duplicates_dict = analysis_result["no_duplicates_dictionary"]
                no_synonyms_dict = analysis_result["no_synonyms_dictionary"]
                logger.info("Использован ИИ-анализатор для анализа аспектов")
            except Exception as e:
                logger.warning(f"Ошибка ИИ-анализатора, используем локальный: {e}")
                analysis_result = await aspect_analyzer.analyze_reviews(reviews_with_ratings, request.product_name)
                general_dict = analysis_result["general_dictionary"]
                no_duplicates_dict = analysis_result["no_duplicates_dictionary"]
                no_synonyms_dict = analysis_result["no_synonyms_dictionary"]
        else:
            analysis_result = await aspect_analyzer.analyze_reviews(reviews_with_ratings, request.product_name)
            general_dict = analysis_result["general_dictionary"]
            no_duplicates_dict = analysis_result["no_duplicates_dictionary"]
            no_synonyms_dict = analysis_result["no_synonyms_dictionary"]
        
        processing_time = asyncio.get_event_loop().time() - start_time
        
        return AspectAnalysisResponse(
            general_dictionary=general_dict,
            no_duplicates_dictionary=no_duplicates_dict,
            no_synonyms_dictionary=no_synonyms_dict,
            processing_time=processing_time
        )
        
    except Exception as e:
        logger.error(f"Error in aspect analysis: {e}")
        raise HTTPException(status_code=500, detail=f"Ошибка анализа: {str(e)}")

@router.post("/analyze-single-review", response_model=SingleReviewAspectResponse)
async def analyze_single_review_aspects(
    request: SingleReviewAspectRequest
):
    """Анализ аспектов отдельного отзыва"""
    start_time = asyncio.get_event_loop().time()

    try:
        # Анализируем аспекты одного отзыва используя ИИ, если доступен
        if ai_aspect_analyzer:
            try:
                aspects_result = await ai_aspect_analyzer.analyze_single_review(
                    request.review_text, 
                    request.rating
                )
                logger.info("Использован ИИ-анализатор для анализа одного отзыва")
            except Exception as e:
                logger.warning(f"Ошибка ИИ-анализатора, используем локальный: {e}")
                aspects_result = await aspect_analyzer.analyze_single_review(
                    request.review_text, 
                    request.rating
                )
        else:
            aspects_result = await aspect_analyzer.analyze_single_review(
                request.review_text, 
                request.rating
            )

        processing_time = asyncio.get_event_loop().time() - start_time

        return SingleReviewAspectResponse(
            positive_aspects=aspects_result["positive"],
            negative_aspects=aspects_result["negative"],
            processing_time=processing_time
        )

    except Exception as e:
        logger.error(f"Error in single review analysis: {e}")
        raise HTTPException(status_code=500, detail=f"Ошибка анализа: {str(e)}")

@router.post("/generate-dictionary", response_model=List[str])
async def generate_dictionary(
    request: AspectDictionaryRequest,
    db: AsyncSession = Depends(get_db)
):
    """Генерация словаря аспектов на основе существующих аспектов"""
    try:
        # Используем ИИ-анализатор, если доступен, иначе локальный
        if ai_aspect_analyzer:
            try:
                no_synonyms_dict = await ai_aspect_analyzer.generate_custom_dictionary(
                    request.aspects,
                    request.synonym_journal
                )
                logger.info("Использован ИИ-анализатор для генерации словаря")
                return no_synonyms_dict
            except Exception as e:
                logger.warning(f"Ошибка ИИ-анализатора, используем локальный: {e}")
                no_synonyms_dict = await aspect_analyzer.generate_custom_dictionary(
                    request.aspects,
                    request.synonym_journal
                )
                return no_synonyms_dict
        else:
            no_synonyms_dict = await aspect_analyzer.generate_custom_dictionary(
                request.aspects,
                request.synonym_journal
            )
            return no_synonyms_dict
        
    except Exception as e:
        logger.error(f"Error generating dictionary: {e}")
        raise HTTPException(status_code=500, detail=f"Ошибка генерации словаря: {str(e)}")

@router.post("/test-first-30", response_model=AspectAnalysisResponse)
async def test_first_30_feedbacks(
    product_name: str = "Тестовый товар",
    db: AsyncSession = Depends(get_db)
):
    """Тестирование ИИ-анализатора на первых 30 отзывах из БД"""
    start_time = asyncio.get_event_loop().time()
    
    try:
        # Получаем первые 30 отзывов из БД
        query = select(Feedback).order_by(Feedback.id.asc()).limit(30)
        result = await db.execute(query)
        feedbacks = result.scalars().all()
        
        if not feedbacks:
            raise HTTPException(status_code=404, detail="Отзывы не найдены в БД")
        
        logger.info(f"🧪 ТЕСТ: Анализируем первые {len(feedbacks)} отзывов из БД")
        
        # Формируем список отзывов с оценками
        reviews_with_ratings = []
        for feedback in feedbacks:
            review_text = feedback.text or ""
            rating = feedback.rating or 0
            reviews_with_ratings.append(f"{review_text}; Оценка {rating}/5")
        
        # Анализируем через ИИ
        if ai_aspect_analyzer:
            try:
                analysis_result = await ai_aspect_analyzer.analyze_reviews(reviews_with_ratings, product_name)
                general_dict = analysis_result["general_dictionary"]
                no_duplicates_dict = analysis_result["no_duplicates_dictionary"]
                no_synonyms_dict = analysis_result["no_synonyms_dictionary"]
                logger.info("✅ ТЕСТ: ИИ-анализатор успешно проанализировал отзывы")
                
                # TODO: Сохраняем аспекты в БД для каждого отзыва
                await _save_aspects_to_feedbacks(db, feedbacks, analysis_result)
                
            except Exception as e:
                logger.error(f"❌ ТЕСТ: Ошибка ИИ-анализатора: {e}")
                # Fallback на локальный анализатор
                analysis_result = await aspect_analyzer.analyze_reviews(reviews_with_ratings, product_name)
                general_dict = analysis_result["general_dictionary"]
                no_duplicates_dict = analysis_result["no_duplicates_dictionary"]
                no_synonyms_dict = analysis_result["no_synonyms_dictionary"]
                logger.info("⚠️ ТЕСТ: Использован локальный анализатор")
        else:
            analysis_result = await aspect_analyzer.analyze_reviews(reviews_with_ratings, product_name)
            general_dict = analysis_result["general_dictionary"]
            no_duplicates_dict = analysis_result["no_duplicates_dictionary"]
            no_synonyms_dict = analysis_result["no_synonyms_dictionary"]
            logger.info("⚠️ ТЕСТ: ИИ-анализатор недоступен, использован локальный")
        
        processing_time = asyncio.get_event_loop().time() - start_time
        
        return AspectAnalysisResponse(
            general_dictionary=general_dict,
            no_duplicates_dictionary=no_duplicates_dict,
            no_synonyms_dictionary=no_synonyms_dict,
            processing_time=processing_time
        )
        
    except Exception as e:
        logger.error(f"❌ ТЕСТ: Ошибка в тестировании: {e}")
        raise HTTPException(status_code=500, detail=f"Ошибка тестирования: {str(e)}")

async def _save_aspects_to_feedbacks(db: AsyncSession, feedbacks: List[Feedback], analysis_result: Dict):
    """Сохранение аспектов в БД для каждого отзыва"""
    try:
        # Получаем общий словарь аспектов
        all_aspects = analysis_result.get("no_synonyms_dictionary", [])
        
        for feedback in feedbacks:
            # Анализируем каждый отзыв отдельно для получения его аспектов
            if ai_aspect_analyzer:
                try:
                    single_result = await ai_aspect_analyzer.analyze_single_review(
                        feedback.text or "", 
                        feedback.rating or 0
                    )
                    
                    # Сохраняем аспекты в JSON поле
                    feedback.aspects = {
                        "positive": single_result.get("positive", []),
                        "negative": single_result.get("negative", []),
                        "all_aspects": all_aspects,
                        "analyzed_at": datetime.now().isoformat()
                    }
                    
                except Exception as e:
                    logger.warning(f"Не удалось проанализировать отзыв {feedback.id}: {e}")
                    # Сохраняем только общие аспекты
                    feedback.aspects = {
                        "positive": [],
                        "negative": [],
                        "all_aspects": all_aspects,
                        "analyzed_at": datetime.now().isoformat(),
                        "error": str(e)
                    }
        
        # Сохраняем изменения в БД
        await db.commit()
        logger.info(f"✅ Сохранены аспекты для {len(feedbacks)} отзывов в БД")
        
    except Exception as e:
        logger.error(f"❌ Ошибка сохранения аспектов в БД: {e}")
        await db.rollback()

@router.get("/health")
async def health_check():
    """Проверка состояния сервиса"""
    return {"status": "healthy", "service": "aspect-analysis"}
