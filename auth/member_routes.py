import uuid

from fastapi import APIRouter

from auth.database import session_scope
from auth.deps import CurrentUserDep
from auth.members import (
    create_sub_account,
    delete_sub_account,
    list_sub_accounts,
    member_to_dict,
    reset_sub_account_password,
    update_sub_account,
)
from auth.schemas import (
    MemberCreateRequest,
    MemberListResponse,
    MemberPublic,
    MemberResetPasswordRequest,
    MemberUpdateRequest,
    OkResponse,
)
from auth.tenant import assert_manage_members

router = APIRouter(prefix="/api/tenant", tags=["tenant"])


def _require_owner(user: CurrentUserDep) -> None:
    assert_manage_members(user)


@router.get("/members", response_model=MemberListResponse)
async def list_members(user: CurrentUserDep) -> MemberListResponse:
    _require_owner(user)
    async with session_scope() as session:
        members = await list_sub_accounts(session, uuid.UUID(user.tenant_id))
    return MemberListResponse(members=[MemberPublic(**member_to_dict(m)) for m in members])


@router.post("/members", response_model=MemberPublic)
async def create_member(payload: MemberCreateRequest, user: CurrentUserDep) -> MemberPublic:
    _require_owner(user)
    async with session_scope() as session:
        member = await create_sub_account(
            session,
            tenant_id=uuid.UUID(user.tenant_id),
            username=payload.username,
            password=payload.password,
            role=payload.role,
        )
    return MemberPublic(**member_to_dict(member))


@router.patch("/members/{member_id}", response_model=MemberPublic)
async def patch_member(member_id: str, payload: MemberUpdateRequest, user: CurrentUserDep) -> MemberPublic:
    _require_owner(user)
    async with session_scope() as session:
        member = await update_sub_account(
            session,
            tenant_id=uuid.UUID(user.tenant_id),
            user_id=uuid.UUID(member_id),
            role=payload.role,
            status=payload.status,
        )
    return MemberPublic(**member_to_dict(member))


@router.delete("/members/{member_id}", response_model=OkResponse)
async def remove_member(member_id: str, user: CurrentUserDep) -> OkResponse:
    _require_owner(user)
    async with session_scope() as session:
        await delete_sub_account(
            session,
            tenant_id=uuid.UUID(user.tenant_id),
            user_id=uuid.UUID(member_id),
        )
    return OkResponse(ok=True)


@router.post("/members/{member_id}/reset-password", response_model=OkResponse)
async def reset_member_password(
    member_id: str,
    payload: MemberResetPasswordRequest,
    user: CurrentUserDep,
) -> OkResponse:
    _require_owner(user)
    async with session_scope() as session:
        await reset_sub_account_password(
            session,
            tenant_id=uuid.UUID(user.tenant_id),
            user_id=uuid.UUID(member_id),
            password=payload.password,
        )
    return OkResponse(ok=True)
