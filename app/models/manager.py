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
        self._model_configs.clear()
        self.discover_models()
        
        # Ensure default model is registered
        if settings.DEFAULT_MODEL not in self._models:
            from app.models.context_aware import ContextAwareModel
            self.register_model(settings.DEFAULT_MODEL, ContextAwareModel)
    
    def discover_models(self):
        """
        Auto-discover and load all models from the specified directories.
        First scan app/models directory for built-in models,
        then scan models directory for extension models.
        
        Each model should be a separate directory containing:
        - main.py: Model main program
        - config.yaml: Configuration file (optional)
        - requirements.txt: Dependencies file (optional)
        - data/: Data directory (optional)
        """
        # 1. 先扫描 app/models 目录下的内置模型
        try:
            app_models_dir = Path(__file__).parent
            logger.info(f"Scanning built-in models directory: {app_models_dir}")
            
            for item in app_models_dir.iterdir():
                if item.is_dir() and not item.name.startswith('_') and not item.name.startswith('.'):
                    try:
                        # 检查是否存在必要的文件
                        main_file = item / "main.py"
                        config_file = item / "config.yaml"
                        
                        if not main_file.exists():
                            logger.warning(f"Skipping built-in model {item.name}: main.py not found")
                            continue
                            
                        # 加载配置文件
                        config = {}
                        if config_file.exists():
                            with open(config_file) as f:
                                config = yaml.safe_load(f)
                        
                        # 加载模型模块
                        module_name = f"app.models.{item.name}.main"
                        
                        # 尝试直接导入模块
                        try:
                            module = importlib.import_module(module_name)
                        except ImportError:
                            # 如果直接导入失败，尝试使用spec加载
                            spec = importlib.util.spec_from_file_location(
                                module_name,
                                str(main_file)
                            )
                            module = importlib.util.module_from_spec(spec)
                            sys.modules[module_name] = module
                            spec.loader.exec_module(module)
                        
                        # 查找模型类
                        for name, obj in inspect.getmembers(module):
                            if (inspect.isclass(obj) 
                                and issubclass(obj, AnythingBaseModel) 
                                and obj != AnythingBaseModel):
                                model_name = item.name
                                self.register_model(model_name, obj)
                                self._model_configs[model_name] = config
                                logger.info(f"Discovered built-in model: {model_name}")
                                break
                                
                    except Exception as e:
                        logger.error(f"Error loading built-in model {item.name}: {str(e)}")
        except Exception as e:
            logger.error(f"Error discovering built-in models: {str(e)}")
        
        # 2. 再扫描 models 目录下的扩展模型
        try:
            # 使用配置中指定的模型目录
            models_dir = Path(settings.MODELS_DIR)
            logger.info(f"Scanning extension models directory: {models_dir}")
            
            if not models_dir.exists():
                logger.warning(f"Extension models directory {models_dir} does not exist")
                return
                
            for item in models_dir.iterdir():
                if item.is_dir() and not item.name.startswith('_') and not item.name.startswith('.'):
                    try:
                        # 检查是否存在必要的文件
                        main_file = item / "main.py"
                        config_file = item / "config.yaml"
                        
                        if not main_file.exists():
                            logger.warning(f"Skipping extension model {item.name}: main.py not found")
                            continue
                            
                        # 加载配置文件
                        config = {}
                        if config_file.exists():
                            with open(config_file) as f:
                                config = yaml.safe_load(f)
                        
                        # 加载模型模块
                        module_name = f"models.{item.name}.main"
                        spec = importlib.util.spec_from_file_location(
                            module_name,
                            str(main_file)
                        )
                        module = importlib.util.module_from_spec(spec)
                        sys.modules[module_name] = module
                        spec.loader.exec_module(module)
                        
                        # 查找模型类
                        for name, obj in inspect.getmembers(module):
                            if (inspect.isclass(obj) 
                                and issubclass(obj, AnythingBaseModel) 
                                and obj != AnythingBaseModel):
                                model_name = item.name
                                self.register_model(model_name, obj)
                                self._model_configs[model_name] = config
                                logger.info(f"Discovered extension model: {model_name}")
                                break
                                
                    except Exception as e:
                        logger.error(f"Error loading extension model {item.name}: {str(e)}")
        except Exception as e:
            logger.error(f"Error discovering extension models: {str(e)}")
    
    def register_model(self, name: str, model_class: Type[AnythingBaseModel]):
        """
        Register a new model.

        Args:
            name: Model name.
            model_class: Model class.
        """
        self._models[name] = model_class
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
            # Always create a new instance for each request to ensure independent state
            if name in self._models:
                model = self._models[name]()
                # Set model directory
                model.model_dir = Path(settings.MODELS_DIR) / name
                # Set configuration to model instance if available
                if name in self._model_configs:
                    model.config = self._model_configs[name]
                return model
            return None
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
        This will reinitialize the model registry and configurations.
        """
        self._init_models()
        logger.info("All models reloaded")

# Create global model manager instance
model_manager = ModelManager() 