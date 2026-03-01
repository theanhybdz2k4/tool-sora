"""
Common helper functions for Sora automation (Playwright version)
"""
import time
from typing import Callable, Any


def wait_for_condition(
    condition: Callable[[], bool],
    timeout: int = 10,
    interval: float = 0.5,
    error_message: str = "Condition not met"
) -> bool:
    """
    Generic wait helper that polls a condition function
    
    Args:
        condition: Function that returns True when condition is met
        timeout: Maximum time to wait in seconds
        interval: Time between checks in seconds
        error_message: Message to log if timeout occurs
        
    Returns:
        True if condition met, False if timeout
    """
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            if condition():
                return True
        except Exception:
            pass
        time.sleep(interval)
    return False


def retry_on_exception(
    func: Callable,
    max_retries: int = 3,
    delay: float = 1.0,
    exceptions: tuple = (Exception,)
) -> Any:
    """
    Retry a function on exception
    
    Args:
        func: Function to retry
        max_retries: Maximum number of retries
        delay: Delay between retries in seconds
        exceptions: Tuple of exceptions to catch
        
    Returns:
        Result of function call
        
    Raises:
        Last exception if all retries fail
    """
    last_exception = None
    for attempt in range(max_retries):
        try:
            return func()
        except exceptions as e:
            last_exception = e
            if attempt < max_retries - 1:
                time.sleep(delay)
    raise last_exception


def find_element_by_text(page, text: str, element_type: str = "*", timeout: int = 5000) -> Any:
    """
    Find element by visible text content using Playwright
    
    Args:
        page: Playwright Page instance
        text: Text to search for
        element_type: HTML element type (default: any)
        timeout: Maximum time to wait in ms
        
    Returns:
        Locator if found, None otherwise
    """
    try:
        locator = page.get_by_text(text, exact=False)
        locator.wait_for(timeout=timeout)
        return locator
    except Exception:
        return None


def safe_click(page, selector: str, force: bool = False) -> bool:
    """
    Safely click an element with fallback to JavaScript
    
    Args:
        page: Playwright Page instance
        selector: CSS selector
        force: Force click without waiting for actionability
        
    Returns:
        True if successful, False otherwise
    """
    try:
        page.click(selector, force=force)
        return True
    except Exception:
        try:
            page.evaluate(f"document.querySelector('{selector}').click()")
            return True
        except Exception:
            return False


def get_element_text(page, selector: str, default: str = "") -> str:
    """
    Safely get element text content
    
    Args:
        page: Playwright Page instance
        selector: CSS selector
        default: Default value if text cannot be retrieved
        
    Returns:
        Element text or default value
    """
    try:
        return page.text_content(selector) or default
    except Exception:
        return default


def is_element_visible(page, selector: str) -> bool:
    """
    Check if element is visible on page
    
    Args:
        page: Playwright Page instance
        selector: CSS selector
        
    Returns:
        True if visible, False otherwise
    """
    try:
        return page.is_visible(selector)
    except Exception:
        return False


def wait_for_page_load(page, timeout: int = 30000):
    """
    Wait for page to finish loading
    
    Args:
        page: Playwright Page instance
        timeout: Maximum time to wait in ms
    """
    page.wait_for_load_state("domcontentloaded", timeout=timeout)
