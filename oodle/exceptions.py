class ExitThread(Exception):
    """Raised when the thread should exit. This exception can be thrown into a thread from other threads."""