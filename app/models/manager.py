from typing import Dict, Type, Optional
import importlib
import inspect
import pkgutil
from pathlib import Path
import yaml
import sys
import shutil
from app.models.base import AnythingBaseModel
from app.models.echo import EchoModel
from app.models.context_aware import ContextAwareModel
from app.core.config import settings
from app.core.logger import get_logger

logger = get_logger("model_manager")

class ModelManager:
    """
    Model manager responsible for managing all available models.
    Supports loading models from specified directories.
    """
    
    _instance = None
    _models: Dict[str, Type[AnythingBaseModel]] = {}
    _instances: Dict[str, AnythingBaseModel] = {}
    _model_configs: Dict[str, dict] = {}  # Store model configurations
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._init_models()
        return cls._instance
    
    def _init_models(self):
        """
        Initialize available models.
        Load all models through auto-discovery mechanism.
        """
        self._models.clear()
        self._instances.clear()
        self._model_configs.clear()
        self.discover_models()
        
        # Ensure default model is registered
        if settings.DEFAULT_MODEL not in self._models:
            from app.models.context_aware import ContextAwareModel
            self.register_model(settings.DEFAULT_MODEL, ContextAwareModel)
    
    def discover_models(self):
        """
        Auto-discover and load all models from the specified directory.
        Each model should be a separate directory containing:
        - main.py: Model main program
        - config.yaml: Configuration file (optional)
        - requirements.txt: Dependencies file (optional)
        - data/: Data directory (optional)
        """
        try:
            # Use model directory specified in configuration
            models_dir = Path(settings.MODELS_DIR)
            if not models_dir.exists():
                logger.warning(f"Models directory {models_dir} does not exist")
                return
                
            for item in models_dir.iterdir():
                if item.is_dir() and not item.name.startswith('_'):
                    try:
                        # Check if necessary files exist
                        main_file = item / "main.py"
                        config_file = item / "config.yaml"
                        
                        if not main_file.exists():
                            logger.warning(f"Skipping {item.name}: main.py not found")
                            continue
                            
                        # Load configuration file
                        config = {}
                        if config_file.exists():
                            with open(config_file) as f:
                                config = yaml.safe_load(f)
                        
                        # Load model module
                        module_name = f"models.{item.name}.main"
                        spec = importlib.util.spec_from_file_location(
                            module_name,
                            str(main_file)
                        )
                        module = importlib.util.module_from_spec(spec)
                        sys.modules[module_name] = module
                        spec.loader.exec_module(module)
                        
                        # Find model class
                        for name, obj in inspect.getmembers(module):
                            if (inspect.isclass(obj) 
                                and issubclass(obj, AnythingBaseModel) 
                                and obj != AnythingBaseModel):
                                model_name = item.name
                                self.register_model(model_name, obj)
                                self._model_configs[model_name] = config
                                logger.info(f"Discovered model: {model_name}")
                                break
                                
                    except Exception as e:
                        logger.error(f"Error loading model {item.name}: {str(e)}")
        except Exception as e:
            logger.error(f"Error discovering models: {str(e)}")
    
    def register_model(self, name: str, model_class: Type[AnythingBaseModel]):
        """
        Register a new model.

        Args:
            name: Model name.
            model_class: Model class.
        """
        self._models[name] = model_class
        # Clear existing instance (if any)
        self._instances.pop(name, None)
        logger.info(f"Registered model: {name}")
    
    def get_model(self, name: str) -> Optional[AnythingBaseModel]:
        """
        Get model instance.

        Args:
            name: Model name.

        Returns:
            Model instance, or None if model doesn't exist.
        """
        try:
            # Create new instance if it doesn't exist
            if name not in self._instances and name in self._models:
                model = self._models[name]()
                # Set model directory
                model.model_dir = Path(settings.MODELS_DIR) / name
                # Set configuration to model instance if available
                if name in self._model_configs:
                    model.config = self._model_configs[name]
                self._instances[name] = model
            return self._instances.get(name)
        except Exception as e:
            logger.error(f"Error creating model instance {name}: {str(e)}")
            return None
    
    def list_models(self) -> Dict[str, dict]:
        """
        List all available models and their configuration information.

        Returns:
            Dictionary of model information.
        """
        return {
            name: {
                "config": self._model_configs.get(name, {}),
                "class": model_class.__name__
            }
            for name, model_class in self._models.items()
        }
    
    def reload_models(self):
        """
        Reload all models.
        This will clear all existing model instances.
        """
        self._init_models()
        logger.info("All models reloaded")

# Create global model manager instance
model_manager = ModelManager() 