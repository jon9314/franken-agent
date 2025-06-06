import httpx
import json
from typing import List, Optional, Dict, Tuple, Any # <-- 'Any' has been added here
from loguru import logger

from app.core.config import settings, OllamaServer

class OllamaService:
    def __init__(self, servers: List[OllamaServer]):
        self.servers = {server.name: server for server in servers}
        self.client = httpx.AsyncClient(timeout=180.0)

    def get_default_server(self) -> Optional[OllamaServer]:
        """Returns the first configured server as the default."""
        if not self.servers:
            return None
        return next(iter(self.servers.values()))

    async def list_models_from_server(self, server: OllamaServer) -> List[Dict[str, str]]:
        """Fetches models from a specific Ollama server."""
        try:
            response = await self.client.get(f"{server.url}/api/tags")
            response.raise_for_status()
            models_data = response.json().get("models", [])
            return [{"server_name": server.name, "model_name": model['name'], "url": str(server.url)} for model in models_data]
        except httpx.RequestError as e:
            logger.error(f"Could not connect to Ollama server '{server.name}' at {server.url}. Error: {e}")
        except httpx.HTTPStatusError as e:
            logger.error(f"Ollama server '{server.name}' returned an error: {e.response.status_code} - {e.response.text}")
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON response from Ollama server '{server.name}': {e}")
        return []

    async def list_models(self) -> List[Dict[str, str]]:
        """Fetches the list of available models from all configured Ollama servers."""
        all_models = []
        for server_name, server_config in self.servers.items():
            models_from_server = await self.list_models_from_server(server_config)
            all_models.extend(models_from_server)
        return all_models

    async def _get_target_model_and_server(self, model_name: Optional[str] = None) -> Tuple[OllamaServer, str]:
        """Helper to determine the server and model name to use. Raises ValueError if not found."""
        if not self.servers:
            logger.error("No Ollama servers configured.")
            raise ValueError("No Ollama servers are configured in the settings.")

        if model_name and '/' in model_name:
            server_nickname, specific_model_name = model_name.split('/', 1)
            if server_nickname in self.servers:
                server_to_use = self.servers[server_nickname]
                logger.info(f"Using specified server '{server_nickname}' and model '{specific_model_name}'.")
                return server_to_use, specific_model_name
            else:
                logger.warning(f"Specified server nickname '{server_nickname}' not found in config. Trying to find model '{specific_model_name}' on any server.")
                model_name = specific_model_name

        if model_name:
            all_listed_models = await self.list_models()
            for m_info in all_listed_models:
                if m_info['model_name'] == model_name:
                    server_to_use = self.servers[m_info['server_name']]
                    logger.info(f"Found model '{model_name}' on server '{m_info['server_name']}'.")
                    return server_to_use, model_name
            logger.warning(f"Model '{model_name}' not found on any configured server. Falling back to default model on default server.")

        server_to_use = self.get_default_server()
        if not server_to_use:
            raise ValueError("Could not determine a default Ollama server.")

        models_on_default_server = await self.list_models_from_server(server_to_use)
        if not models_on_default_server:
            raise ValueError(f"No models available on default server '{server_to_use.name}'.")
        
        target_model = models_on_default_server[0]['model_name']
        logger.info(f"Using fallback model '{target_model}' on server '{server_to_use.name}'.")
        return server_to_use, target_model

    async def _make_ollama_request(self, server_url: Any, payload: Dict) -> Dict:
        """Internal helper to make the actual HTTP request to Ollama."""
        try:
            url_str = str(server_url)
            response = await self.client.post(f"{url_str}/api/generate", json=payload)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            logger.error(f"Ollama server at {server_url} returned status {e.response.status_code}: {e.response.text}")
            error_detail = f"Ollama server error: {e.response.status_code}."
            try:
                ollama_error = e.response.json().get("error")
                if ollama_error:
                    error_detail += f" Message: {ollama_error}"
            except json.JSONDecodeError:
                pass 
            return {"error": error_detail, "_raw_error_content": e.response.text}
        except httpx.RequestError as e:
            logger.error(f"Request to Ollama server at {server_url} failed: {e}")
            return {"error": f"Failed to communicate with Ollama server: {str(e)}"}
        except Exception as e:
            logger.error(f"Unexpected error making request to Ollama server at {server_url}: {e}")
            return {"error": f"Unexpected error with Ollama server: {str(e)}"}

    async def generate(self, prompt: str, model_name: Optional[str] = None) -> Dict:
        """Sends a prompt to an Ollama server and gets a plain text response."""
        server_to_use, target_model = await self._get_target_model_and_server(model_name)
        logger.info(f"Sending prompt to model '{target_model}' on server '{server_to_use.name}' ({server_to_use.url}).")
        payload = {"model": target_model, "prompt": prompt, "stream": False}
        
        ollama_response = await self._make_ollama_request(server_to_use.url, payload)
        if "error" in ollama_response:
            return ollama_response
            
        return {
            "response": ollama_response.get("response", "").strip(),
            "model_used": target_model
        }

    async def generate_json(self, prompt: str, model_name: Optional[str] = None) -> Dict:
        """Sends a prompt to an Ollama server and requests a JSON response."""
        server_to_use, target_model = await self._get_target_model_and_server(model_name)
        logger.info(f"Sending JSON prompt to model '{target_model}' on server '{server_to_use.name}' ({server_to_use.url}).")
        payload = {"model": target_model, "prompt": prompt, "format": "json", "stream": False}
        
        ollama_response_raw = await self._make_ollama_request(server_to_use.url, payload)
        if "error" in ollama_response_raw:
            return ollama_response_raw

        response_text_json_string = ollama_response_raw.get("response", "{}")
        try:
            return json.loads(response_text_json_string)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to decode JSON from Ollama response: {e}. Raw response string: '{response_text_json_string}'")
            return {"error": "Ollama returned an invalid JSON string that could not be parsed."}

ollama_service = OllamaService(servers=settings.OLLAMA_SERVERS)
