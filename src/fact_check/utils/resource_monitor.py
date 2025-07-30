"""Resource monitoring utilities for parallel processing."""

import psutil
import logging
from typing import Optional, Callable
import asyncio

logger = logging.getLogger(__name__)


class ResourceMonitor:
    """Monitor system resources during parallel processing."""
    
    def __init__(
        self,
        memory_threshold_percent: float = 80.0,
        check_interval: float = 1.0
    ):
        """
        Initialize resource monitor.
        
        Args:
            memory_threshold_percent: Max memory usage before throttling
            check_interval: How often to check resources (seconds)
        """
        self.memory_threshold = memory_threshold_percent
        self.check_interval = check_interval
        self._monitoring = False
        self._pause_event = asyncio.Event()
        self._pause_event.set()  # Start unpaused
        
    async def start_monitoring(self):
        """Start background resource monitoring."""
        self._monitoring = True
        asyncio.create_task(self._monitor_loop())
        
    async def stop_monitoring(self):
        """Stop resource monitoring."""
        self._monitoring = False
        
    async def _monitor_loop(self):
        """Background loop to monitor resources."""
        while self._monitoring:
            memory_percent = psutil.virtual_memory().percent
            
            if memory_percent > self.memory_threshold:
                logger.warning(
                    f"⚠️  Memory usage high: {memory_percent:.1f}% "
                    f"(threshold: {self.memory_threshold}%)"
                )
                self._pause_event.clear()  # Pause new work
                
                # Wait for memory to drop
                while memory_percent > (self.memory_threshold - 10):  # Hysteresis
                    await asyncio.sleep(self.check_interval)
                    memory_percent = psutil.virtual_memory().percent
                    
                logger.info(f"✅ Memory recovered: {memory_percent:.1f}%")
                self._pause_event.set()  # Resume
            
            await asyncio.sleep(self.check_interval)
    
    async def wait_if_paused(self):
        """Wait if resource usage is too high."""
        await self._pause_event.wait()
    
    def get_current_stats(self) -> dict:
        """Get current resource statistics."""
        memory = psutil.virtual_memory()
        return {
            "memory_percent": memory.percent,
            "memory_available_gb": memory.available / (1024**3),
            "memory_used_gb": memory.used / (1024**3),
            "cpu_percent": psutil.cpu_percent(interval=0.1)
        }


class MemoryLimitedSemaphore:
    """Semaphore that also checks memory before acquiring."""
    
    def __init__(
        self,
        max_concurrent: int,
        memory_threshold_percent: float = 80.0
    ):
        self._semaphore = asyncio.Semaphore(max_concurrent)
        self._memory_threshold = memory_threshold_percent
        
    async def __aenter__(self):
        # Wait for memory to be available
        while psutil.virtual_memory().percent > self._memory_threshold:
            logger.info(
                f"Waiting for memory... Current: {psutil.virtual_memory().percent:.1f}%"
            )
            await asyncio.sleep(1)
            
        # Then acquire semaphore
        await self._semaphore.__aenter__()
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self._semaphore.__aexit__(exc_type, exc_val, exc_tb)