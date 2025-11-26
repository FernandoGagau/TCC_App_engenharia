"""
OpenRouter Service - Intelligent LLM routing and fallback system
Complete implementation with cost optimization and performance monitoring
"""

import os
import httpx
import asyncio
import uuid
import logging
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta
from enum import Enum
import json
import hashlib
from collections import deque
import statistics

logger = logging.getLogger(__name__)


class ModelCapability(Enum):
    """Model capabilities for task matching"""
    TEXT = "text"
    VISION = "vision"
    CODE = "code"
    REASONING = "reasoning"
    SPEED = "speed"
    TRANSLATION = "translation"
    SUMMARIZATION = "summarization"
    CREATIVE = "creative"


class ModelPriority(Enum):
    """Priority levels for model selection"""
    PRIMARY = 1
    SECONDARY = 2
    TERTIARY = 3
    EMERGENCY = 4


class ModelRegistry:
    """
    Registry of available models with their characteristics
    Prices updated as of 2024
    """

    MODELS = {
        # Anthropic Models
        "anthropic/claude-3-opus-20240229": {
            "capabilities": [ModelCapability.TEXT, ModelCapability.REASONING, ModelCapability.CODE, ModelCapability.CREATIVE],
            "max_tokens": 4096,
            "max_context": 200000,
            "cost_per_1k_input": 0.015,
            "cost_per_1k_output": 0.075,
            "priority": ModelPriority.PRIMARY,
            "timeout": 30,
            "quality_score": 0.95,
            "speed_score": 0.7
        },
        "anthropic/claude-3-sonnet-20240229": {
            "capabilities": [ModelCapability.TEXT, ModelCapability.CODE, ModelCapability.REASONING],
            "max_tokens": 4096,
            "max_context": 200000,
            "cost_per_1k_input": 0.003,
            "cost_per_1k_output": 0.015,
            "priority": ModelPriority.SECONDARY,
            "timeout": 20,
            "quality_score": 0.90,
            "speed_score": 0.8
        },
        "anthropic/claude-3-haiku-20240307": {
            "capabilities": [ModelCapability.TEXT, ModelCapability.SPEED, ModelCapability.SUMMARIZATION],
            "max_tokens": 4096,
            "max_context": 200000,
            "cost_per_1k_input": 0.00025,
            "cost_per_1k_output": 0.00125,
            "priority": ModelPriority.TERTIARY,
            "timeout": 10,
            "quality_score": 0.85,
            "speed_score": 0.95
        },

        # Google Models
        "google/gemini-pro": {
            "capabilities": [ModelCapability.TEXT, ModelCapability.CODE, ModelCapability.REASONING],
            "max_tokens": 8192,
            "max_context": 32000,
            "cost_per_1k_input": 0.000125,
            "cost_per_1k_output": 0.000375,
            "priority": ModelPriority.SECONDARY,
            "timeout": 15,
            "quality_score": 0.88,
            "speed_score": 0.85
        },
        "google/gemini-pro-vision": {
            "capabilities": [ModelCapability.VISION, ModelCapability.TEXT],
            "max_tokens": 4096,
            "max_context": 16000,
            "cost_per_1k_input": 0.000125,
            "cost_per_1k_output": 0.000375,
            "priority": ModelPriority.PRIMARY,
            "timeout": 20,
            "quality_score": 0.90,
            "speed_score": 0.75
        },
        "google/gemini-2.0-flash-thinking-exp:free": {
            "capabilities": [ModelCapability.TEXT, ModelCapability.REASONING, ModelCapability.SPEED],
            "max_tokens": 8192,
            "max_context": 32000,
            "cost_per_1k_input": 0.0,  # Free tier
            "cost_per_1k_output": 0.0,
            "priority": ModelPriority.EMERGENCY,
            "timeout": 10,
            "quality_score": 0.80,
            "speed_score": 0.90
        },

        # Meta Models
        "meta-llama/llama-3-70b-instruct": {
            "capabilities": [ModelCapability.TEXT, ModelCapability.SPEED, ModelCapability.CODE],
            "max_tokens": 8192,
            "max_context": 8192,
            "cost_per_1k_input": 0.00059,
            "cost_per_1k_output": 0.00079,
            "priority": ModelPriority.SECONDARY,
            "timeout": 12,
            "quality_score": 0.85,
            "speed_score": 0.88
        },
        "meta-llama/llama-3-8b-instruct": {
            "capabilities": [ModelCapability.TEXT, ModelCapability.SPEED],
            "max_tokens": 8192,
            "max_context": 8192,
            "cost_per_1k_input": 0.000055,
            "cost_per_1k_output": 0.000055,
            "priority": ModelPriority.TERTIARY,
            "timeout": 8,
            "quality_score": 0.75,
            "speed_score": 0.95
        },

        # OpenAI Models
        "openai/gpt-4-turbo": {
            "capabilities": [ModelCapability.TEXT, ModelCapability.CODE, ModelCapability.REASONING, ModelCapability.VISION],
            "max_tokens": 4096,
            "max_context": 128000,
            "cost_per_1k_input": 0.01,
            "cost_per_1k_output": 0.03,
            "priority": ModelPriority.SECONDARY,
            "timeout": 25,
            "quality_score": 0.93,
            "speed_score": 0.75
        },
        "openai/gpt-4o": {
            "capabilities": [ModelCapability.TEXT, ModelCapability.CODE, ModelCapability.VISION, ModelCapability.SPEED],
            "max_tokens": 4096,
            "max_context": 128000,
            "cost_per_1k_input": 0.0025,
            "cost_per_1k_output": 0.01,
            "priority": ModelPriority.PRIMARY,
            "timeout": 20,
            "quality_score": 0.92,
            "speed_score": 0.85
        },
        "openai/gpt-4o-mini": {
            "capabilities": [ModelCapability.TEXT, ModelCapability.SPEED, ModelCapability.CODE],
            "max_tokens": 16384,
            "max_context": 128000,
            "cost_per_1k_input": 0.00015,
            "cost_per_1k_output": 0.0006,
            "priority": ModelPriority.TERTIARY,
            "timeout": 10,
            "quality_score": 0.82,
            "speed_score": 0.92
        },

        # X.AI Models
        "x-ai/grok-2-1212": {
            "capabilities": [ModelCapability.TEXT, ModelCapability.REASONING, ModelCapability.CODE],
            "max_tokens": 131072,
            "max_context": 131072,
            "cost_per_1k_input": 0.002,
            "cost_per_1k_output": 0.01,
            "priority": ModelPriority.SECONDARY,
            "timeout": 20,
            "quality_score": 0.91,
            "speed_score": 0.80
        },
        "x-ai/grok-2-vision-1212": {
            "capabilities": [ModelCapability.VISION, ModelCapability.TEXT, ModelCapability.REASONING],
            "max_tokens": 32768,
            "max_context": 32768,
            "cost_per_1k_input": 0.002,
            "cost_per_1k_output": 0.01,
            "priority": ModelPriority.PRIMARY,
            "timeout": 25,
            "quality_score": 0.90,
            "speed_score": 0.75
        }
    }

    @classmethod
    def get_models_for_capability(cls, capability: ModelCapability) -> List[str]:
        """Get models that support a specific capability"""
        return [
            model for model, info in cls.MODELS.items()
            if capability in info["capabilities"]
        ]

    @classmethod
    def get_models_by_priority(cls, priority: ModelPriority) -> List[str]:
        """Get models by priority level"""
        return [
            model for model, info in cls.MODELS.items()
            if info["priority"] == priority
        ]

    @classmethod
    def estimate_cost(cls, model: str, input_tokens: int, output_tokens: int) -> float:
        """Estimate cost of a request"""
        if model not in cls.MODELS:
            return 0.0

        info = cls.MODELS[model]
        input_cost = (input_tokens / 1000) * info["cost_per_1k_input"]
        output_cost = (output_tokens / 1000) * info["cost_per_1k_output"]
        return input_cost + output_cost

    @classmethod
    def get_quality_speed_score(cls, model: str) -> Tuple[float, float]:
        """Get quality and speed scores for a model"""
        if model not in cls.MODELS:
            return 0.5, 0.5

        info = cls.MODELS[model]
        return info.get("quality_score", 0.5), info.get("speed_score", 0.5)


class CircuitBreaker:
    """Circuit breaker for failing models"""

    def __init__(self, failure_threshold: int = 5, reset_timeout: int = 60):
        self.failure_threshold = failure_threshold
        self.reset_timeout = reset_timeout
        self.failures = {}
        self.last_failure_time = {}

    def is_open(self, model: str) -> bool:
        """Check if circuit is open for a model"""
        if model not in self.failures:
            return False

        # Check if reset timeout has passed
        if model in self.last_failure_time:
            time_since_failure = (datetime.utcnow() - self.last_failure_time[model]).seconds
            if time_since_failure > self.reset_timeout:
                self.reset(model)
                return False

        return self.failures.get(model, 0) >= self.failure_threshold

    def record_failure(self, model: str):
        """Record a failure for a model"""
        self.failures[model] = self.failures.get(model, 0) + 1
        self.last_failure_time[model] = datetime.utcnow()

    def record_success(self, model: str):
        """Record a success and potentially reset the circuit"""
        if model in self.failures:
            self.failures[model] = max(0, self.failures[model] - 1)

    def reset(self, model: str):
        """Reset circuit for a model"""
        self.failures.pop(model, None)
        self.last_failure_time.pop(model, None)


class ResponseCache:
    """Cache for model responses"""

    def __init__(self, max_size: int = 1000, ttl_seconds: int = 3600):
        self.cache = {}
        self.timestamps = {}
        self.max_size = max_size
        self.ttl_seconds = ttl_seconds
        self.access_order = deque(maxlen=max_size)

    def _generate_key(self, model: str, messages: List[Dict], **kwargs) -> str:
        """Generate cache key from request parameters"""
        cache_data = {
            "model": model,
            "messages": messages,
            **kwargs
        }
        cache_str = json.dumps(cache_data, sort_keys=True)
        return hashlib.md5(cache_str.encode()).hexdigest()

    def get(self, model: str, messages: List[Dict], **kwargs) -> Optional[Dict]:
        """Get cached response if available and not expired"""
        key = self._generate_key(model, messages, **kwargs)

        if key in self.cache:
            # Check if expired
            if datetime.utcnow() - self.timestamps[key] < timedelta(seconds=self.ttl_seconds):
                # Update access order
                self.access_order.remove(key)
                self.access_order.append(key)
                return self.cache[key]
            else:
                # Remove expired entry
                del self.cache[key]
                del self.timestamps[key]

        return None

    def set(self, model: str, messages: List[Dict], response: Dict, **kwargs):
        """Cache a response"""
        key = self._generate_key(model, messages, **kwargs)

        # Evict oldest if at capacity
        if len(self.cache) >= self.max_size and key not in self.cache:
            oldest_key = self.access_order[0]
            del self.cache[oldest_key]
            del self.timestamps[oldest_key]

        self.cache[key] = response
        self.timestamps[key] = datetime.utcnow()
        if key in self.access_order:
            self.access_order.remove(key)
        self.access_order.append(key)


class OpenRouterService:
    """
    Main OpenRouter service with intelligent fallback and cost optimization
    """

    def __init__(self, api_key: str, config: Dict[str, Any]):
        self.api_key = api_key
        self.config = config
        self.base_url = "https://openrouter.ai/api/v1"

        # HTTP client with retries
        self.client = httpx.AsyncClient(
            timeout=httpx.Timeout(60.0, connect=10.0),
            limits=httpx.Limits(max_keepalive_connections=5, max_connections=10),
            headers={
                "Authorization": f"Bearer {api_key}",
                "HTTP-Referer": config.get("referer", "https://construction-analysis.ai"),
                "X-Title": config.get("app_title", "Construction Analysis Agent")
            }
        )

        # Components
        self.circuit_breaker = CircuitBreaker()
        self.response_cache = ResponseCache()
        self.performance_history = {}

        # Configuration
        self.max_retries = config.get("MAX_RETRIES", 3)
        self.cost_threshold = config.get("COST_THRESHOLD_USD", 0.10)
        self.latency_threshold = config.get("LATENCY_THRESHOLD_MS", 5000)

        logger.info("OpenRouter service initialized")

    async def complete(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        task_type: str = "text",
        max_retries: Optional[int] = None,
        use_cache: bool = True,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Complete a request with automatic fallback

        Args:
            messages: Chat messages
            model: Specific model to use (optional)
            task_type: Type of task (text, vision, code, reasoning)
            max_retries: Override default max retries
            use_cache: Whether to use response cache
            **kwargs: Additional parameters for the API

        Returns:
            Response dictionary with completion and metadata
        """

        if max_retries is None:
            max_retries = self.max_retries

        # Check cache first
        if use_cache and model:
            cached_response = self.response_cache.get(model, messages, **kwargs)
            if cached_response:
                logger.info(f"Cache hit for model {model}")
                return {**cached_response, "cached": True}

        # Select model if not specified
        if not model:
            model = await self._select_model(task_type, messages)
            logger.info(f"Selected model {model} for task type {task_type}")

        # Get fallback chain
        fallback_models = self._get_fallback_chain(model, task_type)

        # Try primary and fallback models
        attempt = 0
        errors = []

        for current_model in [model] + fallback_models[:max_retries]:
            # Check circuit breaker
            if self.circuit_breaker.is_open(current_model):
                logger.warning(f"Circuit breaker open for {current_model}, skipping")
                continue

            attempt += 1
            start_time = datetime.utcnow()

            try:
                # Check estimated cost
                estimated_cost = await self._estimate_request_cost(current_model, messages)
                if estimated_cost > self.cost_threshold:
                    logger.warning(f"Estimated cost ${estimated_cost:.4f} exceeds threshold for {current_model}")
                    # Try to find cheaper alternative
                    alternative = await self._find_cheaper_alternative(current_model, task_type)
                    if alternative != current_model:
                        logger.info(f"Switching to cheaper model {alternative}")
                        current_model = alternative

                # Make request
                response = await self._make_request(current_model, messages, **kwargs)

                # Calculate metrics
                latency_ms = (datetime.utcnow() - start_time).total_seconds() * 1000

                # Record success
                self.circuit_breaker.record_success(current_model)
                await self._record_performance(current_model, latency_ms, True)

                # Cache successful response
                if use_cache:
                    self.response_cache.set(current_model, messages, response, **kwargs)

                # Add metadata
                response["model_used"] = current_model
                response["fallback_attempt"] = attempt - 1
                response["latency_ms"] = latency_ms
                response["estimated_cost"] = estimated_cost

                logger.info(f"Request completed with {current_model} in {latency_ms:.2f}ms")
                return response

            except Exception as e:
                # Record failure
                self.circuit_breaker.record_failure(current_model)
                await self._record_performance(current_model, -1, False)

                errors.append({
                    "model": current_model,
                    "error": str(e),
                    "attempt": attempt
                })

                logger.error(f"Model {current_model} failed (attempt {attempt}): {e}")

                # Wait before retry with exponential backoff
                if attempt < len([model] + fallback_models[:max_retries]):
                    await asyncio.sleep(2 ** (attempt - 1))

        # All attempts failed
        error_msg = f"All models failed after {attempt} attempts. Errors: {json.dumps(errors, indent=2)}"
        logger.error(error_msg)
        raise Exception(error_msg)

    async def _select_model(self, task_type: str, messages: List[Dict]) -> str:
        """Select best model for the task"""

        # Check for vision requirement
        has_images = any(
            isinstance(msg.get("content"), list) and
            any(item.get("type") == "image_url" for item in msg["content"])
            if isinstance(msg.get("content"), list)
            else False
            for msg in messages
        )

        if has_images:
            # Get vision-capable models
            vision_models = ModelRegistry.get_models_for_capability(ModelCapability.VISION)
            # Prefer models with best quality/cost ratio
            vision_models.sort(key=lambda m: (
                ModelRegistry.MODELS[m]["priority"].value,
                ModelRegistry.MODELS[m]["cost_per_1k_input"]
            ))
            return vision_models[0] if vision_models else "google/gemini-pro-vision"

        # Calculate context size
        total_chars = sum(
            len(msg.get("content", "")) if isinstance(msg.get("content"), str)
            else sum(len(item.get("text", "")) for item in msg.get("content", []) if item.get("type") == "text")
            for msg in messages
        )

        # Task-specific selection
        if task_type == "reasoning":
            candidates = ModelRegistry.get_models_for_capability(ModelCapability.REASONING)
        elif task_type == "code":
            candidates = ModelRegistry.get_models_for_capability(ModelCapability.CODE)
        elif task_type == "speed" or total_chars < 1000:
            candidates = ModelRegistry.get_models_for_capability(ModelCapability.SPEED)
        else:
            candidates = ModelRegistry.get_models_for_capability(ModelCapability.TEXT)

        # Filter by context window
        estimated_tokens = total_chars / 4  # Rough estimation
        candidates = [
            m for m in candidates
            if ModelRegistry.MODELS[m]["max_context"] > estimated_tokens
        ]

        if not candidates:
            # Fallback to default
            return self.config.get("PRIMARY_MODEL", "anthropic/claude-3-sonnet-20240229")

        # Sort by priority and cost
        candidates.sort(key=lambda m: (
            ModelRegistry.MODELS[m]["priority"].value,
            ModelRegistry.MODELS[m]["cost_per_1k_input"]
        ))

        return candidates[0]

    async def _make_request(
        self,
        model: str,
        messages: List[Dict],
        **kwargs
    ) -> Dict[str, Any]:
        """Make request to OpenRouter API"""

        # Get model configuration
        model_info = ModelRegistry.MODELS.get(model, {})

        # Prepare payload
        payload = {
            "model": model,
            "messages": messages,
            "max_tokens": min(
                kwargs.get("max_tokens", 1000),
                model_info.get("max_tokens", 4096)
            ),
            "temperature": kwargs.get("temperature", 0.7),
            "top_p": kwargs.get("top_p", 1.0),
            "stream": kwargs.get("stream", False),
            "stop": kwargs.get("stop"),
            "frequency_penalty": kwargs.get("frequency_penalty", 0),
            "presence_penalty": kwargs.get("presence_penalty", 0),
        }

        # Remove None values
        payload = {k: v for k, v in payload.items() if v is not None}

        # Make request with timeout
        timeout = model_info.get("timeout", 30)

        try:
            response = await self.client.post(
                f"{self.base_url}/chat/completions",
                json=payload,
                timeout=timeout
            )

            response.raise_for_status()
            return response.json()

        except httpx.TimeoutException:
            raise Exception(f"Request to {model} timed out after {timeout}s")
        except httpx.HTTPStatusError as e:
            error_detail = e.response.text if e.response else str(e)
            raise Exception(f"HTTP {e.response.status_code}: {error_detail}")
        except Exception as e:
            raise Exception(f"Request failed: {str(e)}")

    def _get_fallback_chain(self, primary_model: str, task_type: str) -> List[str]:
        """Get fallback chain for a model"""

        # Get required capability
        capability_map = {
            "text": ModelCapability.TEXT,
            "vision": ModelCapability.VISION,
            "code": ModelCapability.CODE,
            "reasoning": ModelCapability.REASONING,
            "speed": ModelCapability.SPEED
        }

        required_capability = capability_map.get(task_type, ModelCapability.TEXT)

        # Get compatible models
        compatible_models = ModelRegistry.get_models_for_capability(required_capability)

        # Remove primary model and broken models
        fallback_models = [
            m for m in compatible_models
            if m != primary_model and not self.circuit_breaker.is_open(m)
        ]

        # Sort by priority, quality, and cost
        fallback_models.sort(key=lambda m: (
            ModelRegistry.MODELS[m]["priority"].value,
            -ModelRegistry.MODELS[m]["quality_score"],
            ModelRegistry.MODELS[m]["cost_per_1k_input"]
        ))

        # Add emergency free model as last resort
        free_models = [m for m in ModelRegistry.MODELS if ModelRegistry.MODELS[m]["cost_per_1k_input"] == 0]
        if free_models:
            fallback_models.extend([m for m in free_models if m not in fallback_models])

        return fallback_models

    async def _find_cheaper_alternative(self, model: str, task_type: str) -> str:
        """Find cheaper alternative for a model"""

        current_cost = ModelRegistry.MODELS[model]["cost_per_1k_input"]
        alternatives = self._get_fallback_chain(model, task_type)

        for alt in alternatives:
            alt_cost = ModelRegistry.MODELS[alt]["cost_per_1k_input"]
            alt_quality = ModelRegistry.MODELS[alt]["quality_score"]

            # Accept if significantly cheaper and quality is acceptable
            if alt_cost < current_cost * 0.5 and alt_quality >= 0.8:
                return alt

        return model  # Keep original if no good alternative

    async def _estimate_request_cost(
        self,
        model: str,
        messages: List[Dict],
        estimated_output_tokens: int = 500
    ) -> float:
        """Estimate cost of a request"""

        # Estimate input tokens
        total_chars = sum(
            len(msg.get("content", "")) if isinstance(msg.get("content"), str)
            else sum(len(item.get("text", "")) for item in msg.get("content", []) if item.get("type") == "text")
            for msg in messages
        )
        estimated_input_tokens = int(total_chars / 4)  # Rough approximation

        return ModelRegistry.estimate_cost(
            model,
            estimated_input_tokens,
            estimated_output_tokens
        )

    async def _record_performance(self, model: str, latency_ms: float, success: bool):
        """Record performance metrics for a model"""

        if model not in self.performance_history:
            self.performance_history[model] = {
                "latencies": deque(maxlen=100),
                "success_count": 0,
                "failure_count": 0,
                "total_requests": 0
            }

        history = self.performance_history[model]
        history["total_requests"] += 1

        if success:
            history["success_count"] += 1
            if latency_ms > 0:
                history["latencies"].append(latency_ms)
        else:
            history["failure_count"] += 1

    def get_model_stats(self, model: str) -> Dict[str, Any]:
        """Get performance statistics for a model"""

        if model not in self.performance_history:
            return {}

        history = self.performance_history[model]
        latencies = list(history["latencies"])

        if not latencies:
            return {
                "total_requests": history["total_requests"],
                "success_rate": history["success_count"] / max(1, history["total_requests"]),
                "failure_count": history["failure_count"]
            }

        return {
            "total_requests": history["total_requests"],
            "success_rate": history["success_count"] / max(1, history["total_requests"]),
            "failure_count": history["failure_count"],
            "avg_latency_ms": statistics.mean(latencies),
            "p50_latency_ms": statistics.median(latencies),
            "p95_latency_ms": statistics.quantiles(latencies, n=20)[-1] if len(latencies) > 1 else latencies[0],
            "p99_latency_ms": statistics.quantiles(latencies, n=100)[-1] if len(latencies) > 10 else max(latencies)
        }

    def get_all_model_stats(self) -> Dict[str, Dict[str, Any]]:
        """Get performance statistics for all models"""
        return {
            model: self.get_model_stats(model)
            for model in self.performance_history
        }

    async def health_check(self) -> Dict[str, Any]:
        """Check health of the service"""

        try:
            # Try a simple request with the cheapest model
            test_messages = [{"role": "user", "content": "Hi"}]
            response = await self.complete(
                test_messages,
                model="google/gemini-2.0-flash-thinking-exp:free",
                max_tokens=10,
                use_cache=False
            )

            return {
                "status": "healthy",
                "models_available": len(ModelRegistry.MODELS),
                "circuit_breakers_open": sum(
                    1 for m in ModelRegistry.MODELS
                    if self.circuit_breaker.is_open(m)
                ),
                "cache_size": len(self.response_cache.cache),
                "performance_tracking": len(self.performance_history)
            }

        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e),
                "models_available": len(ModelRegistry.MODELS),
                "circuit_breakers_open": sum(
                    1 for m in ModelRegistry.MODELS
                    if self.circuit_breaker.is_open(m)
                )
            }

    async def close(self):
        """Close the service and clean up resources"""
        await self.client.aclose()