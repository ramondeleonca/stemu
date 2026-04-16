import sys


def _strip_multiprocessing_args(argv):
    cleaned = []
    for arg in argv:
        if arg.startswith("--multiprocessing-fork"):
            continue
        if arg.startswith("parent_pid="):
            continue
        if arg.startswith("pipe_handle="):
            continue
        cleaned.append(arg)
    argv[:] = cleaned


_strip_multiprocessing_args(sys.argv)
