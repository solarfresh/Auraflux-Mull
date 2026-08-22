class Queue:
    MULL = 'mull'


class ProcessRepositoryChunk:
    name = "process_repository_chunk_task"
    queue = Queue.MULL


class ProcessRepositoryFile:
    name = "process_repository_file_task"
    queue = Queue.MULL
