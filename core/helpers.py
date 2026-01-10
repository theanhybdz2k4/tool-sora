"""
Common helper functions for Sora automation
"""
import time
from typing import Callable, Any
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException


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


def find_element_by_text(
    driver,
    text: str,
    element_type: str = "*",
    timeout: int = 5,
    case_sensitive: bool = False
) -> Any:
    """
    Find element by visible text content
    
    Args:
        driver: Selenium WebDriver instance
        text: Text to search for
        element_type: HTML element type (default: any)
        timeout: Maximum time to wait
        case_sensitive: Whether search is case sensitive
        
    Returns:
        WebElement if found, None otherwise
    """
    try:
        if case_sensitive:
            xpath = f"//{element_type}[contains(text(), '{text}')]"
        else:
            xpath = f"//{element_type}[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), '{text.lower()}')]"
        
        wait = WebDriverWait(driver, timeout)
        return wait.until(EC.presence_of_element_located((By.XPATH, xpath)))
    except TimeoutException:
        return None


def safe_click(driver, element, use_js: bool = False) -> bool:
    """
    Safely click an element with fallback to JavaScript
    
    Args:
        driver: Selenium WebDriver instance
        element: Element to click
        use_js: Force use of JavaScript click
        
    Returns:
        True if successful, False otherwise
    """
    try:
        if use_js:
            driver.execute_script("arguments[0].click();", element)
        else:
            try:
                element.click()
            except Exception:
                # Fallback to JS click
                driver.execute_script("arguments[0].click();", element)
        return True
    except Exception:
        return False


def scroll_to_element(driver, element, align_to_top: bool = True):
    """
    Scroll element into view
    
    Args:
        driver: Selenium WebDriver instance
        element: Element to scroll to
        align_to_top: Whether to align to top of viewport
    """
    driver.execute_script(
        f"arguments[0].scrollIntoView({{block: '{'start' if align_to_top else 'center'}'}});",
        element
    )
    time.sleep(0.3)  # Wait for scroll animation


def get_element_text(element, default: str = "") -> str:
    """
    Safely get element text content
    
    Args:
        element: WebElement
        default: Default value if text cannot be retrieved
        
    Returns:
        Element text or default value
    """
    try:
        return element.text or element.get_attribute("textContent") or default
    except Exception:
        return default


def is_element_visible(element) -> bool:
    """
    Check if element is visible on page
    
    Args:
        element: WebElement to check
        
    Returns:
        True if visible, False otherwise
    """
    try:
        return element.is_displayed() and element.is_enabled()
    except Exception:
        return False


def wait_for_page_load(driver, timeout: int = 30):
    """
    Wait for page to finish loading
    
    Args:
        driver: Selenium WebDriver instance
        timeout: Maximum time to wait
    """
    WebDriverWait(driver, timeout).until(
        lambda d: d.execute_script("return document.readyState") == "complete"
    )
