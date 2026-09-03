from unittest.mock import patch

import pytest
from core.constants import ProcessStatus
from repositories.tasks import process_concept_synthesis_task

@pytest.mark.django_db
@patch('repositories.tasks.get_raw_redis_client')
@patch('repositories.tasks.publish_event')
def test_process_concept_synthesis_success(
    mock_publish_event,
    mock_get_redis,
    mock_redis,
    valid_chunk_payload,
    valid_agent_output,
    create_repository_file,
    create_embedding_config
):
    mock_get_redis.return_value = mock_redis
    file_id = str(create_repository_file.id)

    payload = {
        'file_id': file_id,
        'chunk_payload': valid_chunk_payload,
        'agent_output': valid_agent_output,
        'is_premium': True
    }

    process_concept_synthesis_task("event_type", payload)

    mock_publish_event.delay.assert_called_once()

# Missing file_id Case (Returns immediately without Redis decrement)
@patch('repositories.tasks.get_raw_redis_client')
def test_process_concept_synthesis_missing_file_id(
    mock_get_redis,
    mock_redis,
    valid_chunk_payload,
    valid_agent_output
):
    mock_get_redis.return_value = mock_redis

    payload = {
        'file_id': None,
        'chunk_payload': valid_chunk_payload,
        'agent_output': valid_agent_output
    }

    process_concept_synthesis_task("event_type", payload)

    # Ensure Redis counter is NEVER touched when file_id is invalid/missing
    mock_redis.decr.assert_not_called()


# 3. Missing Payload Parameters (chunk_payload or agent_output missing)
@pytest.mark.django_db
@patch('repositories.tasks.get_raw_redis_client')
@patch('repositories.tasks.mark_file_status')
def test_process_concept_synthesis_missing_payload_data(
    mock_mark_status,
    mock_get_redis,
    mock_redis,
    valid_chunk_payload,
    create_repository_file
):
    mock_get_redis.return_value = mock_redis
    file_id = str(create_repository_file.id)

    payload = {
        'file_id': file_id,
        'chunk_payload': valid_chunk_payload,
        'agent_output': None  # Missing agent output
    }

    process_concept_synthesis_task("event_type", payload)

    mock_mark_status.assert_called_once_with(file_id, ProcessStatus.ERROR)
    mock_redis.decr.assert_called_once_with(f"file:{file_id}:pending_chunks")

@pytest.mark.django_db
@patch('repositories.tasks.get_raw_redis_client')
@patch('repositories.tasks.mark_file_status')
def test_process_concept_synthesis_corrupted_json(
    mock_mark_status,
    mock_get_redis,
    mock_redis,
    valid_chunk_payload,
    create_repository_file
):
    mock_get_redis.return_value = mock_redis
    file_id = str(create_repository_file.id)

    payload = {
        'file_id': file_id,
        'chunk_payload': valid_chunk_payload,
        'agent_output': '{ invalid_json: '  # Corrupted JSON
    }

    process_concept_synthesis_task("event_type", payload)

    mock_mark_status.assert_called_once_with(file_id, ProcessStatus.ERROR)
    mock_redis.decr.assert_called_once_with(f"file:{file_id}:pending_chunks")

@pytest.mark.django_db
@patch('repositories.tasks.get_raw_redis_client')
@patch('repositories.tasks.mark_file_status')
def test_process_concept_synthesis_embedding_config_not_found(
    mock_mark_status,
    mock_get_redis,
    mock_redis,
    valid_chunk_payload,
    valid_agent_output,
    create_repository_file
):
    mock_get_redis.return_value = mock_redis
    file_id = str(create_repository_file.id)

    payload = {
        'file_id': file_id,
        'chunk_payload': valid_chunk_payload,
        'agent_output': valid_agent_output
    }

    process_concept_synthesis_task("event_type", payload)

    mock_mark_status.assert_called_once_with(file_id, ProcessStatus.ERROR)
    mock_redis.decr.assert_called_once_with(f"file:{file_id}:pending_chunks")