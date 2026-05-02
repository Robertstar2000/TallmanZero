from helpers.api import ApiHandler, Request, Response

from helpers import runtime
from helpers import self_update


class SelfUpdateGet(ApiHandler):
    @classmethod
    def get_methods(cls) -> list[str]:
        return ["GET", "POST"]

    async def process(self, input: dict, request: Request) -> dict | Response:
        supported = runtime.is_dockerized() and self_update.is_self_update_enabled()
        if not supported:
            return {
                "success": True,
                "supported": False,
                "error": self_update.get_self_update_disabled_reason(),
                "pending": None,
                "last_status": None,
            }

        try:
            info = self_update.get_update_info()
            return {
                "success": True,
                "supported": supported,
                **info,
            }
        except Exception as e:
            return {
                "success": False,
                "supported": supported,
                "error": str(e),
                "pending": self_update.load_pending_update(),
                "last_status": self_update.load_last_status(),
            }
