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
from app.db.vector_store import vector_store
from app.utils.vectorizer import vectorizer

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
            
        # 将所有模型描述添加到向量存储
        # 注意：异步方法需要在异步上下文中调用，这里只是初始化
        # 实际添加操作在reload_models方法中执行
    
    async def _add_models_to_vector_store(self):
        """
        将所有已注册模型的描述添加到向量存储
        """
        logger.info("Adding model descriptions to vector store")
        for model_name, config in self._model_configs.items():
            try:
                # 检查配置中是否启用了向量存储
                vector_store_config = config.get("vector_store", {})
                
                if not vector_store_config.get("enabled", True):
                    logger.debug(f"Vector store disabled for model {model_name}, skipping")
                    continue
                
                # 获取模型描述和元数据
                model_info = config.get("model_info", {})
                description = model_info.get("description", f"{model_name} 模型")
                
                metadata = vector_store_config.get("metadata", {
                    "type": model_name,
                    "capabilities": []
                })
                
                # 生成模型ID
                model_id = f"model-{model_name}"
                
                # 向量化描述
                vector = vectorizer.encode(description)
                
                # 添加到向量存储
                success = await vector_store.add_model_description(
                    model_id,
                    description,
                    vector.tolist(),
                    metadata
                )
                
                if success:
                    logger.info(f"Added model {model_name} description to vector store")
                else:
                    logger.warning(f"Failed to add model {model_name} description to vector store")
                    
            except Exception as e:
                logger.error(f"Error adding model {model_name} to vector store: {str(e)}")
    
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
    
    def add_models_to_vector_store(self):
        """
        将所有模型描述添加到向量存储的同步方法，用于应用启动时调用
        """
        import asyncio
        try:
            # 在新的事件循环中运行异步任务
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(self._add_models_to_vector_store())
            loop.close()
            logger.info("Successfully added all model descriptions to vector store")
        except Exception as e:
            logger.error(f"Error adding model descriptions to vector store: {str(e)}")
    
    def reload_models(self):
        """
        Reload all models.
        This will clear all existing model instances.
        """
        self._init_models()
        logger.info("All models reloaded")
        
        # 重新添加模型描述到向量存储
        self.add_models_to_vector_store()
        logger.info("Model descriptions added to vector store")

# Create global model manager instance
model_manager = ModelManager() 