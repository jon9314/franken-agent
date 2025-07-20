import httpx
import json
import socket
from typing import List, Optional, Dict, Tuple, Any
from loguru import logger

from app.core.config import settings, OllamaServer


def _resolve_docker_host() -> str:
    """Return the IP address of ``host.docker.internal`` if resolvable."""
    try:
        return socket.gethostbyname("host.docker.internal")
    except Exception as exc:
        logger.debug(f"Could not resolve host.docker.internal: {exc}")
        return "host.docker.internal"

class OllamaService:
    def __init__(self, servers: List[OllamaServer]):
        self.servers = {server.name: server for server in servers}
        if not self.servers:
            logger.error("OLLAMA_SERVERS is not configured in the settings.")
            raise ValueError("OLLAMA_SERVERS configuration is missing.")

    async def list_models(self) -> List[Dict[str, str]]:
        """Fetches the list of available models from all configured Ollama servers."""
        all_models = []
        for server_name, server_config in self.servers.items():
            try:
                async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
                    url_to_check = str(server_config.url)
                    if "host.docker.internal" in url_to_check:
                        url_to_check = url_to_check.replace(
                            "host.docker.internal", _resolve_docker_host()
                        )

                    logger.info(f"Checking for models on Ollama server '{server_config.name}' at {url_to_check}")
                    response = await client.get(f"{url_to_check.rstrip('/')}/api/tags")
                    response.raise_for_status()

                    data = response.json()
                    models_data = data.get("models", [])

                    for model in models_data:
                        all_models.append({
                            "server_name": server_config.name,
                            "model_name": model.get("name"),
                        })

                    logger.info(f"Found {len(models_data)} models on server '{server_config.name}'.")

            except Exception as e:
                logger.error(f"An unexpected error occurred while fetching models from '{server_config.name}': {e}", exc_info=True)

        return all_models

    async def _get_target_server(self, model_identifier: str) -> Tuple[Optional[OllamaServer], str]:
        """
        Finds the correct server and model name based on the combined 'server_name/model:tag' string.
        """
        if '/' in model_identifier:
            server_nickname, specific_model_name = model_identifier.split('/', 1)
            if server_nickname in self.servers:
                logger.info(f"Request for model '{specific_model_name}' on explicitly named server '{server_nickname}'.")
                return self.servers[server_nickname], specific_model_name
            else:
                logger.warning(f"Server nickname '{server_nickname}' not found. Searching for model '{specific_model_name}' on all servers.")
                model_name_to_find = specific_model_name
        else:
            model_name_to_find = model_identifier

        # Fallback: Find the model on any available server if not explicitly specified or nickname not found.
        all_models_list = await self.list_models() # This uses the corrected list_models logic
        for model_info in all_models_list:
            if model_info['model_name'] == model_name_to_find:
                server_name = model_info['server_name']
                logger.info(f"Found model '{model_name_to_find}' on server '{server_name}' via search.")
                return self.servers[server_name], model_name_to_find

        # If the model is not found anywhere, we cannot proceed.
        logger.error(f"Could not find model '{model_name_to_find}' on any configured server.")
        return None, model_name_to_find

    async def generate(self, prompt: str, model: Optional[str] = None) -> Dict[str, Any]:
        """Sends a prompt to the appropriate Ollama server and gets a plain text response."""
        if not model:
            return {"error": "No model was selected for generation."}

        server_to_use, target_model = await self._get_target_server(model)

        if not server_to_use:
            error_msg = f"Could not find the specified model '{target_model}' on any configured Ollama server."
            logger.error(error_msg)
            return {"error": error_msg}

        logger.info(f"Sending prompt to model '{target_model}' on server '{server_to_use.name}'.")

        url_str = str(server_to_use.url)
        if "host.docker.internal" in url_str:
            url_str = url_str.replace(
                "host.docker.internal", _resolve_docker_host()
            )

        payload = {"model": target_model, "prompt": prompt, "stream": False}

        try:
            async with httpx.AsyncClient(timeout=180.0, follow_redirects=True) as client:
                response = await client.post(f"{url_str.rstrip('/')}/api/generate", json=payload)
                response.raise_for_status()
                ollama_response = response.json()

                return {
                    "response": ollama_response.get("response", "").strip(),
                    "model_used": f"{target_model} ({server_to_use.name})"
                }
        except httpx.HTTPStatusError as e:
            error_detail = f"Ollama server returned an error: {e.response.status_code}."
            logger.error(f"{error_detail} - {e.response.text}")
            return {"error": error_detail}
        except Exception as e:
            logger.error(f"An unexpected error occurred during model generation: {e}", exc_info=True)
            return {"error": "An unexpected error occurred while communicating with the AI model."}

# Initialize with settings
ollama_service = OllamaService(servers=settings.OLLAMA_SERVERS)
