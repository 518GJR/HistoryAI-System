from fastapi import APIRouter


router = APIRouter()


@router.get("/ping")
def user_ping():
    """用户模块测试接口。"""
    return {"message": "用户模块接口正常"}
