"""AI 辅助工具路由（润色等）"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.modules.system_config.constants.ai import POLISH_SYSTEM_PROMPT
from app.modules.system_config.service.config_service import ConfigService
from app.shared.api.schemas.base import APIResponse
from app.shared.core.logger import log

router = APIRouter(prefix="/ai", tags=["AI Tools"])


class PolishRequest(BaseModel):
    text: str


class PolishResponse(BaseModel):
    polished: str


@router.post("/polish", response_model=APIResponse[PolishResponse])
async def polish_text(request: PolishRequest):
    """使用配置的 AI 模型润色文本"""
    text = request.text.strip()
    if not text:
        raise HTTPException(status_code=400, detail="文本不能为空")

    # 获取 AI 配置
    ai_config = await ConfigService.get_ai_config()
    if not ai_config.get("enabled", True):
        raise HTTPException(status_code=503, detail="AI 服务未启用")

    base_url = ai_config.get("base_url", "")
    model = ai_config.get("model", "")
    api_key = ai_config.get("api_key", "")
    temperature = float(ai_config.get("temperature", 0.3))
    timeout_val = int(ai_config.get("timeout", 60))

    if not base_url or not model:
        raise HTTPException(status_code=503, detail="AI 服务未配置（base_url / model）")

    try:
        import openai
        client = openai.OpenAI(base_url=base_url, api_key=api_key or "ollama", timeout=timeout_val)
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": POLISH_SYSTEM_PROMPT},
                {"role": "user", "content": text},
            ],
            temperature=temperature,
        )
        polished = response.choices[0].message.content.strip()
        log.info(f"AI polish: {len(text)} chars → {len(polished)} chars")
        return APIResponse(data=PolishResponse(polished=polished))
    except Exception as e:
        log.error(f"AI polish failed: {e}")
        raise HTTPException(status_code=502, detail=f"AI 调用失败: {str(e)}")
