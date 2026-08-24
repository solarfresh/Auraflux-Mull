class Queue:
    MULL = 'mull'
    AGENT = 'agent'


class AgentRequest:
    name = "handle_agent_request"
    queue = Queue.AGENT


class ProcessConceptSynthesis:
    name = "process_concept_synthesis_task"
    queue = Queue.MULL


class ProcessRepositoryChunk:
    name = "process_repository_chunk_task"
    queue = Queue.MULL


class ProcessRepositoryFile:
    name = "process_repository_file_task"
    queue = Queue.MULL


class ProcessTriplesExtractor:
    name = "process_triples_extractor_task"
    queue = Queue.MULL
