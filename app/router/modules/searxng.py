#Модуль веб-поиска через самостоятельно развёрнутый SearXNG.
#
#SearXNG отдаёт JSON, если инстанс настроен с format: json в settings.yml
#(это нужно включить один раз в конфиге самого SearXNG, иначе он по
#умолчанию отдаёт только HTML).

import httpx

from app.router.modules.base import BaseModule, ModuleResult


class SearXNGModule(BaseModule):
    name = "searxng"

    def __init__(self, base_url: str, max_results: int = 5, timeout: float = 10.0) -> None:
        self._base_url = base_url.rstrip("/")
        self._max_results = max_results
        self._timeout = timeout

    async def run(self, query: str) -> ModuleResult:
        params = {"q": query, "format": "json"}

        async with httpx.AsyncClient(timeout=self._timeout) as client:
            response = await client.get(f"{self._base_url}/search", params=params)
            response.raise_for_status()
            data = response.json()

        results = data.get("results", [])[: self._max_results]

        if not results:
            return ModuleResult(
                context_text="",
                cost_usd=0.0,
                meta={"results_count": 0},
            )

        #Собираем компактный текстовый контекст из результатов поиска для передачи в исполнителя
        lines = []
        for r in results:
            title = r.get("title", "")
            snippet = r.get("content", "")
            url = r.get("url", "")
            lines.append(f"- {title}: {snippet} ({url})")

        context_text = "Результаты веб-поиска:\n" + "\n".join(lines)

        return ModuleResult(
            context_text=context_text,
            cost_usd=0.0,  #свой self-hosted SearXNG — без стоимости за запрос
            meta={"results_count": len(results)},
        )
