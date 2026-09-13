"""Minimal compatibility shim for the Pinecone client on Windows."""


def read_history_file(*args, **kwargs):
    return None


def write_history_file(*args, **kwargs):
    return None


def clear_history(*args, **kwargs):
    return None


__all__ = ['read_history_file', 'write_history_file', 'clear_history']
