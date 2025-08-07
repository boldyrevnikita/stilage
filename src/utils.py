import sys


def check_if_debugger_is_active() -> bool:
    """Returns True if the debugger is currently active"""
    return hasattr(sys, 'gettrace') and sys.gettrace() is not None
