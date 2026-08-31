from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.database import Conversation, HealthProfile, Message, User, get_db
from app.models.schemas import (
    ConversationDetailResponse,
    ConversationResponse,
    HealthProfileRequest,
    HealthProfileResponse,
    MessageResponse,
)
from app.routers.auth import get_current_user

router = APIRouter(prefix="/api", tags=["patient-data"])


@router.get("/conversations", response_model=list[ConversationResponse])
async def list_conversations(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(
            Conversation,
            func.count(Message.id).label("message_count"),
        )
        .outerjoin(Message, Message.conversation_id == Conversation.id)
        .where(Conversation.user_id == current_user.id)
        .group_by(Conversation.id)
        .order_by(Conversation.updated_at.desc())
    )

    rows = result.all()
    return [
        ConversationResponse(
            id=conversation.id,
            title=conversation.title,
            created_at=conversation.created_at,
            updated_at=conversation.updated_at,
            message_count=message_count,
        )
        for conversation, message_count in rows
    ]


@router.get("/conversations/{conversation_id}", response_model=ConversationDetailResponse)
async def get_conversation(
    conversation_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    convo_result = await db.execute(
        select(Conversation).where(
            Conversation.id == conversation_id,
            Conversation.user_id == current_user.id,
        )
    )
    conversation = convo_result.scalar_one_or_none()
    if conversation is None:
        raise HTTPException(status_code=404, detail="Conversation not found")

    msg_result = await db.execute(
        select(Message)
        .where(Message.conversation_id == conversation.id)
        .order_by(Message.created_at.asc())
    )
    messages = msg_result.scalars().all()

    return ConversationDetailResponse(
        id=conversation.id,
        title=conversation.title,
        messages=[
            MessageResponse(
                id=msg.id,
                role=msg.role,
                content=msg.content,
                created_at=msg.created_at,
            )
            for msg in messages
        ],
        created_at=conversation.created_at,
    )


@router.put("/profile", response_model=HealthProfileResponse)
async def upsert_profile(
    payload: HealthProfileRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(HealthProfile).where(HealthProfile.user_id == current_user.id)
    )
    profile = result.scalar_one_or_none()

    if profile is None:
        profile = HealthProfile(user_id=current_user.id)
        db.add(profile)

    for field_name, value in payload.model_dump().items():
        setattr(profile, field_name, value)

    await db.commit()
    await db.refresh(profile)

    return HealthProfileResponse(
        id=profile.id,
        age=profile.age,
        gender=profile.gender,
        height=profile.height,
        weight=profile.weight,
        blood_type=profile.blood_type,
        allergies=profile.allergies,
        medications=profile.medications,
        conditions=profile.conditions,
        exercise_frequency=profile.exercise_frequency,
        smoking_status=profile.smoking_status,
        alcohol_consumption=profile.alcohol_consumption,
        updated_at=profile.updated_at,
    )


@router.get("/profile", response_model=HealthProfileResponse)
async def get_profile(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(HealthProfile).where(HealthProfile.user_id == current_user.id)
    )
    profile = result.scalar_one_or_none()
    if profile is None:
        raise HTTPException(status_code=404, detail="Profile not found")

    return HealthProfileResponse(
        id=profile.id,
        age=profile.age,
        gender=profile.gender,
        height=profile.height,
        weight=profile.weight,
        blood_type=profile.blood_type,
        allergies=profile.allergies,
        medications=profile.medications,
        conditions=profile.conditions,
        exercise_frequency=profile.exercise_frequency,
        smoking_status=profile.smoking_status,
        alcohol_consumption=profile.alcohol_consumption,
        updated_at=profile.updated_at,
    )
