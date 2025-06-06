import os
import importlib
import inspect
from loguru import logger
from typing import Dict, Type, List, Optional # For type hinting

from app.plugins.base_plugin import FrankiePlugin # Ensure base_plugin.py is in app.plugins

class PluginManager:
    def __init__(self, plugin_dir_name: str = "plugins"):
        # Construct absolute path for plugin_dir relative to this file's parent (app directory)
        base_app_path = os.path.dirname(os.path.abspath(__file__)) # .../app/services
        self.plugin_dir_abs_path = os.path.join(os.path.dirname(base_app_path), plugin_dir_name) # .../app/plugins
        self.plugins: Dict[str, Type[FrankiePlugin]] = {}  # Stores plugin_id: plugin_class
        self.load_plugins()

    def load_plugins(self):
        """Dynamically discovers and loads plugins from the plugin directory."""
        logger.info(f"Attempting to load plugins from absolute path: {self.plugin_dir_abs_path}")
        if not os.path.exists(self.plugin_dir_abs_path) or not os.path.isdir(self.plugin_dir_abs_path):
            logger.warning(f"Plugin directory '{self.plugin_dir_abs_path}' not found or is not a directory. No plugins will be loaded.")
            return

        for filename in os.listdir(self.plugin_dir_abs_path):
            # Convention: plugin files end with "_plugin.py" and are not "base_plugin.py"
            if filename.endswith("_plugin.py") and not filename.startswith("base_"):
                module_name_short = filename[:-3] # e.g., "code_modifier_plugin" -> "code_modifier"
                module_name_dotted = f"app.plugins.{module_name_short}" # Dotted path for importlib
                
                try:
                    module = importlib.import_module(module_name_dotted)
                    for name, obj_class in inspect.getmembers(module, inspect.isclass):
                        # Check if it's a subclass of FrankiePlugin and not FrankiePlugin itself
                        if issubclass(obj_class, FrankiePlugin) and obj_class is not FrankiePlugin:
                            try:
                                plugin_id = obj_class.get_id()
                                if plugin_id in self.plugins:
                                    logger.warning(f"Duplicate plugin ID '{plugin_id}' found in {module_name_dotted}. Overwriting previous one from {self.plugins[plugin_id].__module__}.")
                                self.plugins[plugin_id] = obj_class
                                logger.info(f"Successfully loaded plugin '{obj_class.get_name()}' (ID: '{plugin_id}') from {module_name_dotted}.")
                            except Exception as e: # Catch errors during get_id/get_name
                                logger.error(f"Error retrieving ID/Name from plugin class '{name}' in {module_name_dotted}: {e}")
                except ImportError as e:
                    logger.error(f"Failed to import plugin module {module_name_dotted}: {e}")
                except Exception as e:
                    logger.error(f"An unexpected error occurred while loading plugin from {module_name_dotted}: {e}", exc_info=True)
        
        if not self.plugins:
            logger.info("No plugins were loaded from the plugin directory.")
        else:
            logger.info(f"Finished loading plugins. Total loaded: {len(self.plugins)}")

    def get_plugin_class(self, plugin_id: str) -> Optional[Type[FrankiePlugin]]:
        """Returns the class of a registered plugin, or None if not found."""
        plugin_cls = self.plugins.get(plugin_id)
        if not plugin_cls:
            logger.error(f"Plugin with ID '{plugin_id}' not found in loaded plugins: {list(self.plugins.keys())}")
        return plugin_cls

    def list_plugins(self) -> List[Dict[str, str]]:
        """Returns a list of all loaded plugins with their details (id, name, description)."""
        plugin_list = []
        for plugin_id, plugin_class in self.plugins.items():
            try:
                plugin_list.append({
                    "id": plugin_id,
                    "name": plugin_class.get_name(),
                    "description": plugin_class.get_description(),
                })
            except Exception as e: # Catch errors during get_name/get_description
                logger.error(f"Error retrieving details for plugin ID '{plugin_id}': {e}")
        return plugin_list

# Global instance placeholder. This will be instantiated in main.py's on_startup event.
plugin_manager_instance: PluginManager | None = None

def get_plugin_manager() -> PluginManager:
    """
    Provides access to the globally initialized PluginManager instance.
    Raises RuntimeError if it hasn't been initialized (e.g., via app startup).
    """
    if plugin_manager_instance is None:
        logger.critical("PluginManager accessed before App startup initialization!")
        raise RuntimeError("PluginManager has not been initialized. This should occur during application startup.")
    return plugin_manager_instance